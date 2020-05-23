import math
import os

import matplotlib
import numpy as np
import torch
import torchvision
from matplotlib import pyplot as plt
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

import models
from pytorch_hebbian import config, utils

matplotlib.use('TkAgg')
PATH = os.path.dirname(os.path.abspath(__file__))
layer = torch.nn.Module
repu_outputs = torch.zeros(2000)
input_shape = (1, 28, 28)


def hook_fn(_, __, output):
    global repu_outputs
    repu_outputs = output


def plot_weights(weights, activation_indices, filter_conv=True):
    global input_shape

    weights = weights.view(-1, *input_shape)
    weights = weights[activation_indices, :]

    filtered_indices = []
    if filter_conv:
        for j in range(weights.shape[0]):
            unit = weights[j, :].view(-1)
            if torch.sum(torch.pow(torch.abs(unit), 3), 0) < 1.1:
                filtered_indices.append(j)

    weights = weights[filtered_indices, :]
    print(weights.shape[0])

    num_weights = weights.shape[0]
    nrow = math.ceil(math.sqrt(num_weights))
    grid = torchvision.utils.make_grid(weights, nrow=nrow)

    fig = plt.figure()
    if weights.shape[1] == 1:
        grid_np = grid[0, :].cpu().numpy()
        nc = np.amax(np.absolute(grid_np))
        im = plt.imshow(grid_np, cmap='bwr', vmin=-nc, vmax=nc, interpolation='nearest')
        plt.colorbar(im, ticks=[np.amin(grid_np), 0, np.amax(grid_np)])
    else:
        grid_np = np.transpose(grid.cpu().numpy(), (1, 2, 0))
        grid_min = np.amin(grid_np)
        grid_max = np.amax(grid_np)
        grid_np = (grid_np - grid_min) / (grid_max - grid_min)
        plt.imshow(grid_np, interpolation='nearest')
    plt.axis('off')
    fig.tight_layout()
    fig_path = 'activations.png'
    plt.savefig(fig_path, bbox_inches='tight', pad_inches=0.06)
    plt.show()

    return weights


def plot_overlay(activated_weights, inp, activations):
    for i in range(activated_weights.shape[0]):
        unit = activated_weights[i, :].numpy()
        overlay = np.multiply(inp, unit)

        images = [inp, unit, overlay]
        titles = ["input", "unit weights", "multiplied"]
        ticks_min = np.amin(images)
        ticks_max = np.amax(images)
        nc = np.amax(np.absolute(images))
        print(ticks_min, ticks_max, nc)
        fig, axs = plt.subplots(1, 3, sharex=True, sharey=True, figsize=(8, 3))

        im = None
        for j, ax in enumerate(axs):
            image = images[j]
            im = ax.imshow(np.transpose(image, (1, 2, 0))[:, :, 0], cmap='bwr', vmin=-nc, vmax=nc,
                           interpolation='nearest')
            ax.title.set_text(titles[j])

        fig.colorbar(im, ticks=[ticks_min, ticks_max], ax=axs, shrink=0.7)
        fig.suptitle('Activation = {}'.format(activations[i]))
        # fig.tight_layout()
        fig_path = 'combined.png'
        plt.savefig(fig_path, bbox_inches='tight', pad_inches=0.06)
        plt.show()


def visualize_activations(inputs):
    global repu_outputs

    # Iterate over batch
    for i in range(repu_outputs.shape[0]):
        inp = inputs[i, :].numpy()

        sorted_outputs, sorted_indices = torch.sort(repu_outputs[i, :], 0, descending=True)
        cutoff = 0
        print("cutoff = {}".format(cutoff))
        first_neg_index = (sorted_outputs > cutoff).sum(dim=0)
        activation_indices = sorted_indices[:first_neg_index]
        activations = sorted_outputs[:first_neg_index]
        print("activations min: {}, max: {}".format(min(activations), max(activations)))
        print("{} activated neurons".format(len(activation_indices)))

        nc = np.amax(np.absolute(inp))
        im = plt.imshow(np.transpose(inp, (1, 2, 0))[:, :, 0], cmap='bwr', vmin=-nc, vmax=nc, interpolation='nearest')
        plt.colorbar(im, ticks=[np.amin(inp), np.amax(inp)])
        fig_path = 'input.png'
        plt.savefig(fig_path, bbox_inches='tight', pad_inches=0.06)
        plt.show()

        activated_weights = plot_weights(layer.weight, activation_indices)
        plot_overlay(activated_weights, inp, activations)


def main():
    with torch.no_grad():
        global layer
        model = models.create_fc1_model([28 ** 2, 2000], n=1.5, batch_norm=True)
        weights_path = "../../output/models/sup-mnist-fashion-20200523-014847-tl-test_m_62_acc=0.8701.pth"
        layer_names = ['linear1', 'batch_norm']
        # weights_path = "../../output/models/heb-20200417-134912_m_1000_acc=0.8381666666666666.pth"
        # layer_names = [('1', 'linear1')]
        model = utils.load_weights(model, os.path.join(PATH, weights_path), layer_names=layer_names)

        for name, p in model.named_children():
            if name == "repu":
                p.register_forward_hook(hook_fn)
            elif name == "linear1":
                layer = p

        transform = transforms.Compose([
            transforms.ToTensor(),
        ])
        dataset = datasets.mnist.FashionMNIST(root=config.DATASETS_DIR, download=True, transform=transform)
        data_loader = DataLoader(dataset, batch_size=16, shuffle=True)

        for (inputs, labels) in data_loader:
            model(inputs)
            visualize_activations(inputs)
            break


if __name__ == '__main__':
    main()
