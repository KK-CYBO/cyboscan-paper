import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
from sklearn.metrics import classification_report
from sklearn.metrics import roc_curve, auc
from sklearn.preprocessing import label_binarize
import pandas as pd
import numpy as np
import os
import pickle

class TrainingMonitor:
    def __init__(self, output_path, classlist):
        # store the output path for the model, then initialize the list of
        # data points used to plot the loss and accuracy
        self.output_path = output_path
        os.makedirs(output_path, exist_ok=True)
        self.classlist = classlist
        self.lossAcc_init()

    # 最初のEpochを開始する前に全ての値をリセット
    def epochvals_reset(self):
        self.all_labels = []
        self.all_preds = []
        self.all_probs = []
    
    # 各Epochの終了時に値を更新
    def epochvals_update(self, labels, predicted, probs):
        self.all_labels.extend(labels.cpu().numpy())
        self.all_preds.extend(predicted.cpu().numpy())
        self.all_probs.extend(probs.cpu().numpy())

    # Epochごとのサマリーを保存
    def save_epoch_summary(self, epoch):
        # Loss & Accuracy
        self.lossAcc_plot()

        # Confusion Matrix
        self.confMat_plot(epoch)

        # ROC curve & AUC score
        self.rocAuc_plot(epoch)

        # ---- Robust classification report ----
        labels_full = list(range(len(self.classlist)))
        crep = classification_report(
            self.all_labels,
            self.all_preds,
            labels=labels_full,             # ★常に全クラスでレポート
            target_names=self.classlist,
            output_dict=True,
            zero_division=0                 # ★0除算を0扱い
        )
        df = pd.DataFrame(crep).transpose()

        # ---- 二値化評価（LSIL+ / HSIL+）----
        # 既存ポリシーを踏襲（Adenocarcinomaがclasslistにある場合は含める）
        if 'Adenocarcinoma' in self.classlist:
            LSILplus_names = {'LSIL', 'HSIL', 'Adenocarcinoma'}
            HSILplus_names = {'HSIL', 'Adenocarcinoma'}
        else:
            LSILplus_names = {'LSIL', 'HSIL'}
            HSILplus_names = {'HSIL'}

        # classlist にない名前が混じっても安全に（交差を取る）
        name_set = set(self.classlist)
        LSILplus_names = list(LSILplus_names & name_set)
        HSILplus_names = list(HSILplus_names & name_set)

        # 名前→インデックス
        LSILplus_indices = {self.classlist.index(cls) for cls in LSILplus_names}
        HSILplus_indices = {self.classlist.index(cls) for cls in HSILplus_names}

        # 二値化
        LSILplus_binary_labels = [1 if y in LSILplus_indices else 0 for y in self.all_labels]
        LSILplus_binary_preds  = [1 if y in LSILplus_indices else 0 for y in self.all_preds]
        HSILplus_binary_labels = [1 if y in HSILplus_indices else 0 for y in self.all_labels]
        HSILplus_binary_preds  = [1 if y in HSILplus_indices else 0 for y in self.all_preds]

        # 片側しか出現しなくても 2x2 を返すように labels を固定
        cm_lsil = confusion_matrix(LSILplus_binary_labels, LSILplus_binary_preds, labels=[0, 1])
        tn, fp, fn, tp = cm_lsil.ravel()
        LSILplus_sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        LSILplus_specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0

        cm_hsil = confusion_matrix(HSILplus_binary_labels, HSILplus_binary_preds, labels=[0, 1])
        tn, fp, fn, tp = cm_hsil.ravel()
        HSILplus_sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        HSILplus_specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0

        # 保存
        os.makedirs(self.output_path, exist_ok=True)
        with open(f"{self.output_path}/classification_report_e{epoch+1:03d}.txt", "w") as f:
            f.write(df.to_string())
            f.write("\n--------------------------------\n")
            f.write(f"LSIL+ --- Sensitivity: {100*LSILplus_sensitivity:.1f}%  "
                    f"Specificity: {100*LSILplus_specificity:.1f}%\n")
            f.write(f"HSIL+ --- Sensitivity: {100*HSILplus_sensitivity:.1f}%  "
                    f"Specificity: {100*HSILplus_specificity:.1f}%\n")


    # =================================================
    # Loss & Accuracy
    # =================================================
    def lossAcc_init(self):
        self.train_loss_history = []
        self.valid_loss_history = []
        self.train_accuracy_history = []
        self.valid_accuracy_history = []
        self.lossAcc_filepath = f"{self.output_path}/log_loss-accuracy.txt"
        with open(self.lossAcc_filepath, "w") as f:
            f.write("")

    def lossAcc_record(self, loss, accuracy, epoch, type="train"):
        # check to see if the loss should be recorded
        if type == "train":
            self.train_loss_history.append(loss)
            self.train_accuracy_history.append(accuracy)
        elif type == "valid":
            self.valid_loss_history.append(loss)
            self.valid_accuracy_history.append(accuracy)
        with open(self.lossAcc_filepath, "a") as f:
            f.write(f"epoch: {epoch+1}, {type} loss: {loss}, {type} accuracy: {accuracy}\n")

    def lossAcc_plot(self):
        # ensure at least two epochs worth of data have been collected
        if len(self.train_loss_history) == 0:
            return

        # X-axis values starting from 1
        epochs = range(1, len(self.train_loss_history) + 1)

        # Loss curve
        plt.figure(figsize=(10, 6))
        plt.plot(epochs, self.train_loss_history, label="Train Loss")
        plt.plot(epochs, self.valid_loss_history, label="Validation Loss")
        plt.xlabel("Epochs")
        plt.ylabel("Loss")
        plt.title("Loss Curve")
        plt.legend()
        plt.grid()
        plt.savefig(f"{self.output_path}/plot_loss.png")
        plt.close()

        # Accuracy curve
        plt.figure(figsize=(10, 6))
        plt.plot(epochs, self.train_accuracy_history, label="Train Accuracy")
        plt.plot(epochs, self.valid_accuracy_history, label="Validation Accuracy")
        plt.xlabel("Epochs")
        plt.ylabel("Accuracy")
        plt.title("Accuracy Curve")
        plt.legend()
        plt.grid()
        plt.savefig(f"{self.output_path}/plot_accuracy.png")
        plt.close()

    # =================================================
    # Confusion Matrix
    # =================================================

    def confMat_plot(self, epoch):
        cm = confusion_matrix(self.all_labels, self.all_preds, labels=range(len(self.classlist)))

        disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=self.classlist)
        disp.plot(cmap=plt.cm.Blues)
        plt.title(f"Confusion Matrix (Epoch {epoch+1})")
        plt.xticks(rotation=45, ha="right", fontsize=9)  # ラベルを斜めに配置
        plt.yticks(ha="right", fontsize=9)
        for text in disp.text_.ravel():
            text.set_fontsize(7) 
        plt.tight_layout()  # レイアウト調整
        plt.savefig(f"{self.output_path}/confusion-matrix_e{epoch+1:03d}.png")
        plt.close()

        pickle.dump(cm, open(f"{self.output_path}/confusion-matrix_e{epoch+1:03d}.pkl", "wb"))  # 混同行列を保存

    # =================================================
    # ROC curve & AUC score
    # =================================================

    def rocAuc_plot(self, epoch):
        # ラベルをバイナリ化（マルチクラスの場合）
        num_classes = len(self.classlist)
        all_labels_binarized = label_binarize(self.all_labels, classes=range(num_classes))

        # ROC曲線とAUCスコアの計算
        fpr = {}
        tpr = {}
        roc_auc = {}

        for i in range(num_classes):
            fpr[i], tpr[i], _ = roc_curve(all_labels_binarized[:, i], np.array(self.all_probs)[:, i])
            roc_auc[i] = auc(fpr[i], tpr[i])

        # マクロ平均AUC
        fpr["macro"], tpr["macro"], _ = roc_curve(all_labels_binarized.ravel(), np.array(self.all_probs).ravel())
        roc_auc["macro"] = auc(fpr["macro"], tpr["macro"])

        # ROC曲線の描画
        plt.figure(figsize=(10, 8))
        for i in range(num_classes):
            plt.plot(fpr[i], tpr[i], label=f"{self.classlist[i]} (AUC = {roc_auc[i]:.2f})")

        plt.plot(fpr["macro"], tpr["macro"], label=f"Macro Average (AUC = {roc_auc['macro']:.2f})", linestyle="--", color="black")
        plt.plot([0, 1], [0, 1], "k--", lw=2)
        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        plt.title(f"ROC Curve (Epoch {epoch+1})")
        plt.legend(loc="lower right")
        plt.grid()
        plt.savefig(f"{self.output_path}/roc_curve_e{epoch+1:03d}.png")  # ROC曲線を保存
        plt.close()

        output = {
            "fpr": fpr,
            "tpr": tpr,
            "roc_auc": roc_auc
        }
        pickle.dump(output, open(f"{self.output_path}/roc_auc_e{epoch+1:03d}.pkl", "wb"))  # AUCスコアを保存
