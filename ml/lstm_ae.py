"""LSTM autoencoder definition (identical to notebook 02). Needs PyTorch."""
import torch.nn as nn


class LSTMAE(nn.Module):
    def __init__(self, n_features, hidden=64, latent=16):
        super().__init__()
        self.enc = nn.LSTM(n_features, hidden, batch_first=True)
        self.to_latent = nn.Linear(hidden, latent)
        self.from_latent = nn.Linear(latent, hidden)
        self.dec = nn.LSTM(hidden, hidden, batch_first=True)
        self.out = nn.Linear(hidden, n_features)

    def forward(self, x):
        _, (h, _) = self.enc(x)
        z = self.to_latent(h[-1])
        d = self.from_latent(z).unsqueeze(1).repeat(1, x.size(1), 1)
        y, _ = self.dec(d)
        return self.out(y)
