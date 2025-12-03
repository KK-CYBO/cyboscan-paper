import os
import torch
import torch.optim as optim
from torch.utils.data import DataLoader
from model_control import Net, ModelOutput
from training_custom_functions import LMDBdataset, CustomTransform, seed_torch
from training_monitor import TrainingMonitor

DEBUG = False
DEBUG_BATCHNUM = 100

# I/O settings
model_output_root = './output'
lmdb_path = './dataset'
gpu_device_id = 0
gpu_device = f'cuda:{gpu_device_id}'
nametag = os.path.splitext(os.path.basename(__file__))[0]

#----------------------------------------------
# Hyperparameters
#----------------------------------------------
# Basic parameters
basemodel = "maxvit_base_tf_224"
batch_size = 20
num_epochs = 30
initial_lr = 1e-5
dropout_rate = 0.5
patience = 5
classlist = ['Leu', 'Glan', 'Squ.epi', 'Squ.meta','Debris', 'Para.Squ', 'Para.Clust', 'LSIL', 'HSIL', 'Adenocarcinoma']
class_counts = [30, 30, 30, 30, 30, 30, 30, 30, 30, 30]
#----------------------------------------------

# seed_everythin
seed_torch()

# Dataset and DataLoader
transform_train = CustomTransform(coarse_dropout=True)
transform_valid = CustomTransform(coarse_dropout=False)
train_dataset = LMDBdataset(lmdb_path, transform=transform_train, mode="train")
valid_dataset = LMDBdataset(lmdb_path, transform=transform_valid, mode="valid")
train_dataloader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
valid_dataloader = DataLoader(valid_dataset, batch_size=batch_size, shuffle=False)

# Model, optimizer, dropout
device = torch.device(gpu_device if torch.cuda.is_available() else "cpu")
Net_model = Net(basemodel,pretrained=True, num_classes=len(classlist), dropout_rate=dropout_rate)
model = Net_model.to(device)
optimizer = optim.AdamW(model.parameters(), lr=initial_lr, eps=1e-7)

# Loss function
class_ratio = [1 / count for count in class_counts]
class_weights = torch.tensor([ratio / sum(class_ratio) for ratio in class_ratio], device=device)
criterion = torch.nn.CrossEntropyLoss(weight=class_weights)

# Learning rate scheduler
scheduler = optim.lr_scheduler.OneCycleLR(optimizer, max_lr=float(initial_lr), steps_per_epoch=len(train_dataloader), epochs=num_epochs)

# Model output
modelname = f"{nametag}_{len(classlist)}class_{basemodel}.pth"
current_folder = os.path.dirname(os.path.abspath(__file__))
exp_name = os.path.basename(current_folder)                 # Experiment name is folder name
exp_dir = os.path.join(model_output_root, 'exe', exp_name)
mout = ModelOutput(exp_dir, modelname, model, classlist, device, patience)

# Training monitor
logdir = os.path.join(mout.exp_dir, f'logs_{nametag}')
tm = TrainingMonitor(logdir, classlist)

# Training & validation loop
for epoch in range(num_epochs):

    # -------------------
    # Training phase
    # -------------------
    model.train()
    train_loss = 0.0
    correct_train = 0
    total_train = 0
    batchnum = 0
    
    for images, labels in train_dataloader:
        if DEBUG and batchnum > DEBUG_BATCHNUM:    # for debug-----------------------------
            break
        batchnum += 1

        images, labels = images.to(device), labels.to(device)

        # Foward
        outputs = model(images)
        loss = criterion(outputs, labels)

        # Backward and optimize
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        # Update statistics
        train_loss += loss.item()
        _, predicted = outputs.max(1)
        total_train += labels.size(0)
        correct_train += predicted.eq(labels).sum().item()
    
    # Training result
    train_accuracy = 100 * correct_train / total_train
    train_loss = train_loss / len(train_dataloader)
    tm.lossAcc_record(train_loss, train_accuracy, epoch, "train")

    # -------------------
    # Validation phase
    # -------------------
    model.eval()
    valid_loss = 0.0
    correct_valid = 0
    total_valid = 0
    tm.epochvals_reset()
    batchnum = 0
    
    with torch.no_grad():
        for images, labels in valid_dataloader:
            if DEBUG and batchnum > DEBUG_BATCHNUM:    # for debug-----------------------------
                break
            batchnum += 1

            images, labels = images.to(device), labels.to(device)

            # Forward
            outputs = model(images)
            loss = criterion(outputs, labels)

            # Update statistics
            valid_loss += loss.item()
            probs = torch.softmax(outputs, dim=1)
            _, predicted = outputs.max(1)
            total_valid += labels.size(0)
            correct_valid += predicted.eq(labels).sum().item()
            tm.epochvals_update(labels, predicted, probs)

    # Validation result
    valid_accuracy = 100 * correct_valid / total_valid
    valid_loss = valid_loss / len(valid_dataloader)
    tm.lossAcc_record(valid_loss, valid_accuracy, epoch, "valid")

    # Show result for each epoch
    print(f"Epoch [{epoch+1}/{num_epochs}]")
    print(f"  Train Loss: {train_loss:.4f}, Train Accuracy: {train_accuracy:.2f}%")
    print(f"  Valid Loss: {valid_loss:.4f}, Valid Accuracy: {valid_accuracy:.2f}%")
    tm.save_epoch_summary(epoch)

    # Step the learning rate scheduler
    scheduler.step(valid_loss)
    for param_group in optimizer.param_groups:
        print(f"  (Learning rate: {param_group['lr']})")

    # Save model and early stopping
    if mout.save_and_earlystop(model, valid_loss):
        break