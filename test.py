from model.segmentation_model import SegmentationModel
from data.marinedebrisdatamodule import MarineDebrisDataModule
from argparse import Namespace
import argparse
import pytorch_lightning as pl
import os
import pandas as pd
import torch
from PIL import Image
import matplotlib

matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from visualization import rgb
from matplotlib import cm, colors
import numpy as np
import torch
from visualization import rgb, fdi, ndvi


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ckpt-folder', type=str, default="checkpoints/flobs-segm/unet++_2022-10-03_04:00:27")
    parser.add_argument('--data-path', type=str, default="/data/marinedebris")
    parser.add_argument('--batch-size', type=int, default=64)
    parser.add_argument('--weight-decay', type=float, default=1e-12)
    parser.add_argument('--workers', type=int, default=16)
    parser.add_argument('--image-size', type=int, default=128)
    parser.add_argument('--device', type=str, choices=["cpu", "cuda"], default="cuda")

    args = parser.parse_args()

    return args

def main(args):

    ckpt_files = [f for f in os.listdir(args.ckpt_folder) if f.endswith(".ckpt") and f != "last.ckpt"]
    ckpt_file = ckpt_files[0]
    model = SegmentationModel.load_from_checkpoint(checkpoint_path=os.path.join(args.ckpt_folder, ckpt_file))

    marinedebris_datamodule = MarineDebrisDataModule(data_root=args.data_path,
                                        image_size=args.image_size,
                                        workers=args.workers,
                                        batch_size=args.batch_size)

    logger = pl.loggers.csv_logs.CSVLogger(args.ckpt_folder, name="test_log", version=0)
    trainer = pl.Trainer(logger=logger, accelerator="gpu")
    trainer.test(model, marinedebris_datamodule)

    model = model.eval()
    #model = TestTimeAugmentation_wapper(model)

    write_qualitative(model,
                      dataset=marinedebris_datamodule.get_qualitative_test_dataset(),
                      path=os.path.join(args.ckpt_folder, "qualitative"))

class TestTimeAugmentation_wapper(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.threshold = model.threshold

    def forward(self, x):
        y_logits = self.model(x)

        y_logits += torch.fliplr(self.model(torch.fliplr(x)))  # fliplr)
        y_logits += torch.flipud(self.model(torch.flipud(x)))  # flipud

        for rot in [1, 2, 3]:  # 90, 180, 270 degrees
            y_logits += torch.rot90(self.model(torch.rot90(x, rot, [2, 3])), -rot, [2, 3])
        y_logits /= 6

        return y_logits

def write_qualitative(model, dataset, path):
    os.makedirs(path, exist_ok=True)
    for image, id in dataset:
        x = torch.from_numpy(image).float().unsqueeze(0)
        y_score = torch.sigmoid(model(x)).squeeze().detach().numpy()

        fig, ax = plt.subplots()
        ax.imshow(y_score, vmin=0, vmax=1, cmap="Reds")
        ax.axis("off")
        write_path = os.path.join(path, f"{id}_yscore.png")
        fig.savefig(write_path, bbox_inches="tight", pad_inches=0)
        print(f"writing {os.path.abspath(write_path)}")

        fig, ax = plt.subplots()
        ax.imshow(y_score > model.threshold.numpy(), vmin=0, vmax=1, cmap="Reds")
        ax.axis("off")
        write_path = os.path.join(path, f"{id}_ypred.png")
        fig.savefig(write_path, bbox_inches="tight", pad_inches=0)
        print(f"writing {os.path.abspath(write_path)}")

        norm = colors.Normalize(vmin=-0.5, vmax=0.5, clip=True)
        scmap = cm.ScalarMappable(norm=norm, cmap="viridis")
        fig, ax = plt.subplots()
        ax.imshow(scmap.to_rgba(ndvi(x.squeeze(0)).cpu()))
        ax.axis("off")
        write_path = os.path.join(path, f"{id}_ndvi.png")
        fig.savefig(write_path, bbox_inches="tight", pad_inches=0)
        print(f"writing {os.path.abspath(write_path)}")

        norm = colors.Normalize(vmin=-0.1, vmax=0.1, clip=True)
        scmap = cm.ScalarMappable(norm=norm, cmap="magma")
        fig, ax = plt.subplots()
        ax.imshow(scmap.to_rgba(fdi(x.squeeze(0)).cpu()))
        ax.axis("off")
        write_path = os.path.join(path, f"{id}_fdi.png")
        fig.savefig(write_path, bbox_inches="tight", pad_inches=0)
        print(f"writing {os.path.abspath(write_path)}")

        fig, ax = plt.subplots()
        ax.imshow(rgb(x.squeeze(0).cpu().numpy()).transpose(1, 2, 0))
        ax.axis("off")
        write_path = os.path.join(path, f"{id}_rgb.png")
        fig.savefig(write_path, bbox_inches="tight", pad_inches=0)
        print(f"writing {os.path.abspath(write_path)}")

        fig, ax = plt.subplots()
        ax.imshow(rgb(x.squeeze(0).cpu().numpy()).transpose(1, 2, 0))
        ax.contour(y_score, cmap="Reds", vmin=0, vmax=1, levels=8)
        ax.axis("off")
        write_path = os.path.join(path, f"{id}_yscore_overlay.png")
        fig.savefig(write_path, bbox_inches="tight", pad_inches=0)
        print(f"writing {os.path.abspath(write_path)}")

if __name__ == '__main__':
    main(parse_args())
