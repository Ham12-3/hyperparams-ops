"""CIFAR-10 training objective for hyperparameter optimization.

Trains a configurable CNN on CIFAR-10 and returns validation accuracy
as the objective value for Optuna to maximize.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms
from typing import Any


class ConfigurableCNN(nn.Module):
    """A small CNN with configurable depth and dropout."""

    def __init__(self, num_layers: int, dropout: float) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        in_channels = 3
        out_channels = 32

        for i in range(num_layers):
            layers.extend([
                nn.Conv2d(in_channels, out_channels, 3, padding=1),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(),
                nn.MaxPool2d(2) if i < 3 else nn.Identity(),
                nn.Dropout2d(dropout),
            ])
            in_channels = out_channels
            out_channels = min(out_channels * 2, 256)

        self.features = nn.Sequential(*layers)
        self.classifier: nn.Module = nn.Identity()  # built dynamically

    def _build_classifier(self, flat_size: int, dropout: float) -> None:
        self.classifier = nn.Sequential(
            nn.Linear(flat_size, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, 10),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = x.view(x.size(0), -1)
        if isinstance(self.classifier, nn.Identity):
            self._build_classifier(x.size(1), 0.0)
            self.classifier = self.classifier.to(x.device)
        return self.classifier(x)


def get_data_loaders(
    batch_size: int, subset_size: int = 2000
) -> tuple[DataLoader[Any], DataLoader[Any]]:
    """Create CIFAR-10 train and validation data loaders.

    Uses a small subset of the data for fast iteration on CPU.
    Set CIFAR_SUBSET_SIZE env var to control the subset size
    (use 0 for the full dataset).
    """
    import os

    subset_size = int(os.environ.get("CIFAR_SUBSET_SIZE", str(subset_size)))

    transform = transforms.Compose([
        transforms.RandomHorizontalFlip(),
        transforms.RandomCrop(32, padding=4),
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2470, 0.2435, 0.2616)),
    ])

    dataset = datasets.CIFAR10(
        root="/tmp/data", train=True, download=True, transform=transform
    )

    # Use a subset for fast CPU training
    if subset_size > 0 and subset_size < len(dataset):
        dataset, _ = random_split(dataset, [subset_size, len(dataset) - subset_size])

    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_set, val_set = random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_set, batch_size=batch_size, shuffle=False, num_workers=0)
    return train_loader, val_loader


def get_optimizer(
    name: str, parameters: Any, lr: float
) -> optim.Optimizer:
    """Create an optimizer by name."""
    optimizers: dict[str, type[optim.Optimizer]] = {
        "adam": optim.Adam,
        "sgd": optim.SGD,
        "adamw": optim.AdamW,
        "rmsprop": optim.RMSprop,
    }
    return optimizers[name](parameters, lr=lr)


def train_and_evaluate(
    learning_rate: float,
    batch_size: int,
    num_layers: int,
    dropout: float,
    optimizer_name: str,
    max_epochs: int = 10,
    report_callback: Any = None,
) -> float:
    """Train a CNN on CIFAR-10 and return best validation accuracy.

    Args:
        learning_rate: Learning rate for the optimizer.
        batch_size: Training batch size.
        num_layers: Number of conv blocks in the CNN.
        dropout: Dropout probability.
        optimizer_name: Name of the optimizer (adam, sgd, adamw, rmsprop).
        max_epochs: Maximum number of training epochs.
        report_callback: Optional callable(epoch, accuracy) for pruning.

    Returns:
        Best validation accuracy achieved during training.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = ConfigurableCNN(num_layers=num_layers, dropout=dropout)

    # Do a dummy forward pass to build the classifier
    dummy = torch.randn(1, 3, 32, 32)
    model(dummy)

    model = model.to(device)
    optimizer = get_optimizer(optimizer_name, model.parameters(), learning_rate)
    criterion = nn.CrossEntropyLoss()
    train_loader, val_loader = get_data_loaders(batch_size)

    best_accuracy = 0.0

    for epoch in range(max_epochs):
        # Training
        model.train()
        for inputs, targets in train_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()

        # Validation
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, targets in val_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                outputs = model(inputs)
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()

        accuracy = correct / total
        best_accuracy = max(best_accuracy, accuracy)

        if report_callback is not None:
            report_callback(epoch, accuracy)

    return best_accuracy
