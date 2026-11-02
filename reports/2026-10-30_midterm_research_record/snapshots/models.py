"""Agreed pooled teacher and 20,180-parameter masked student."""
import hashlib
import math
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from cesnet_models.models import model_30pktTCNET_256

from data import ROOT, digest


class Teacher(nn.Module):
    def __init__(self, classes, pretrained, cfg):
        super().__init__()
        wrapper = model_30pktTCNET_256(weights=None)
        if pretrained:
            path = ROOT / cfg['pretrained_checkpoint']
            if digest(path) != cfg['pretrained_sha256']:
                raise ValueError('Public checkpoint checksum mismatch')
            state = torch.load(path, map_location='cpu', weights_only=True)
            state.pop('arcface_module.W', None)
            wrapper.load_state_dict(state, strict=True)
        self.backbone = wrapper.backbone_model
        # Auxiliary packet-size counters are not a model input. Official 0.4.1
        # calls histc(Int), unsupported by our CPU Torch. No unseen-embedding
        # replacement is used in this protocol, so disable only the counters.
        self.backbone.save_psizes_hist = False
        self.backbone.mlp_shared = nn.Identity()
        self.backbone.use_mlp_shared = False
        self.head = nn.Linear(448, classes)
        self.freeze_bn_statistics = pretrained

    def train(self, mode=True):
        super().train(mode)
        if mode and self.freeze_bn_statistics:
            for module in self.backbone.modules():
                if isinstance(module, nn.modules.batchnorm._BatchNorm):
                    module.eval()  # affine parameters remain trainable
        return self

    def forward(self, x):
        return self.head(self.backbone.forward_features(x, None))


class Student(nn.Module):
    def __init__(self, classes, drop_channel=None):
        super().__init__()
        self.drop_channel = drop_channel
        self.blocks = nn.ModuleList([nn.Conv1d(3, 32, 3, padding=1),
                                     nn.Conv1d(32, 64, 3, padding=1),
                                     nn.Conv1d(64, 64, 3, padding=1)])
        self.head = nn.Linear(64, classes)

    def forward(self, ppi):
        mask = ppi[:, 1:2] != 0  # before ablation; real zero IPT is valid
        x = torch.stack([torch.log1p(ppi[:, 0]) / math.log1p(65000),
                         ppi[:, 1], ppi[:, 2] / 1500], dim=1)
        if self.drop_channel is not None:
            x = x.clone()
            x[:, self.drop_channel] = 0
        for block in self.blocks:
            x = F.relu(block(x)) * mask
        pooled = (x * mask).sum(-1) / mask.sum(-1).clamp_min(1)
        return self.head(pooled)


def make_model(kind, classes, seed, cfg, load_pretrained=True, drop_channel=None):
    # Reset explicitly: previous teacher forwards/dropout cannot alter student init.
    torch.manual_seed(seed + 10000)
    if kind in ['M1', 'M2']:
        model = Teacher(classes, load_pretrained and kind == 'M2', cfg)
        model.freeze_bn_statistics = kind == 'M2'
        torch.manual_seed(seed + 20000)
        model.head.reset_parameters()  # matched head initialization for M1/M2
    else:
        model = Student(classes, drop_channel)
    expected = 686613 + 449*classes if kind in ['M1', 'M2'] else 18880 + 65*classes
    actual = sum(p.numel() for p in model.parameters())
    if actual != expected:
        raise ValueError(f'{kind}: unexpected architecture {actual} != {expected}')
    return model


def state_digest(model):
    h = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        h.update(name.encode())
        h.update(str((tensor.dtype, tuple(tensor.shape))).encode())
        h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def statistics(ppi):
    mask = ppi[:, 1] != 0
    columns = [mask.sum(1), (ppi[:, 1] == 1).sum(1), (ppi[:, 1] == -1).sum(1),
               ((ppi[:, 1, 1:] != ppi[:, 1, :-1]) & mask[:, 1:] & mask[:, :-1]).sum(1)]
    names = ['packet_count', 'forward_count', 'reverse_count', 'direction_changes']
    for channel, prefix in [(2, 'size'), (0, 'ipt')]:
        values = np.where(mask, ppi[:, channel].astype(np.float64), np.nan)
        for name, fn in [('mean', np.nanmean), ('std', np.nanstd), ('min', np.nanmin),
                         ('max', np.nanmax), ('sum', np.nansum), ('median', np.nanmedian)]:
            columns.append(fn(values, axis=1))
            names.append(f'{prefix}_{name}')
    return np.column_stack(columns).astype('float32'), names


def kd_loss(logits, y, teacher_logits=None, alpha=0.0, temperature=1.0):
    ce = F.cross_entropy(logits, y)
    if teacher_logits is None or alpha == 0:
        return ce
    kd = F.kl_div(F.log_softmax(logits / temperature, dim=1),
                  F.softmax(teacher_logits.detach() / temperature, dim=1), reduction='batchmean')
    return (1-alpha)*ce + alpha*temperature**2*kd
