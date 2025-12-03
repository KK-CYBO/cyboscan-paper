import os
import torch
import torch.nn as nn
import timm


# =================================================
# Model Definition
# =================================================

class Net(nn.Module):
    def __init__(self, basemodel, num_classes, in_chans=3, dropout_rate=0.5, pretrained=True):
        super(Net, self).__init__()
        self.model = timm.create_model(
            basemodel, 
            pretrained=pretrained,  
            num_classes=num_classes, 
            in_chans=in_chans
        )
        self.dropout = nn.Dropout(dropout_rate)

    def forward(self, x):
        x = self.dropout(self.model(x))
        return x

# =================================================
# Model Output (.pth)
# =================================================

class ModelOutput:
    def __init__(self, exp_dir, modelname, model, classlist, device, patience=5):
        self.model = model
        self.classlist = classlist
        self.device = device

        # Create output folder
        self.exp_dir = exp_dir
        os.makedirs(self.exp_dir, exist_ok=True)
        
        # Paths for model output
        self.model_path = os.path.join(self.exp_dir, modelname)
        
        # Early stopping parameters
        self.patience = patience
        self.counter = 0
        self.best_loss = float("inf")


    def save_and_earlystop(self, model, valid_loss):    
        """
        Save the model if the validation loss is the best so far.
        If the validation loss is not improving (when return True), early stop the training.
        """
        self.model = model

        # Early stopping
        if valid_loss < self.best_loss:
            self.best_loss = valid_loss
            self.counter = 0
            # Save the best model
            self.save_model(model)
        else:
            self.counter += 1
            if self.counter >= self.patience:
                print("Early stopping triggered.")
                return True
        
        return False


    def save_model(self, model):    
        # Save model
        torch.save(model.state_dict(), self.model_path)
        self.convert_pth_to_onnx()


    # =================================================
    # Model Conversion (.pth -> .onnx)
    # =================================================

    def convert_pth_to_onnx(self):
        onnx_path = self.model_path.replace(".pth", ".onnx")

        dummy_input = torch.randn(1, 3, 224, 224, device=self.device)
        torch.onnx.export(
            self.model,
            dummy_input,
            onnx_path,
            opset_version=14,
            input_names=['input'],
            output_names=['output'],
            dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
        )
        self.onnx_path = onnx_path
        print(f"Model converted to ONNX: {onnx_path}")
