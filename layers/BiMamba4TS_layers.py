import torch.nn as nn
import torch.nn.functional as F

class Add_Norm(nn.Module):
    def __init__(self, d_model, dropout, residual, drop_flag=1):
        super(Add_Norm, self).__init__()
        self.dropout = nn.Dropout(dropout)
        self.norm = nn.LayerNorm(d_model)
        self.residual = residual
        self.drop_flag = drop_flag
    
    def forward(self, new, old):
        new = self.dropout(new) if self.drop_flag else new
        return self.norm(old + new) if self.residual else self.norm(new)
class singleEncoderLayer(nn.Module):
    def __init__(self, mamba_forward, d_model=128, d_ff=256, dropout=0.1, 
                 activation="relu", residual=1):
        super(singleEncoderLayer, self).__init__()
        self.mamba_forward = mamba_forward
        self.residual = residual
        self.addnorm_for = Add_Norm(d_model, dropout, residual, drop_flag=0)

        self.ffn = nn.Sequential(
            nn.Conv1d(in_channels=d_model, out_channels=d_ff, kernel_size=1),
            nn.ReLU() if activation == "relu" else nn.GELU(),
            nn.Dropout(dropout),
            nn.Conv1d(in_channels=d_ff, out_channels=d_model, kernel_size=1)
        )
        self.addnorm_ffn = Add_Norm(d_model, dropout, residual, drop_flag=1)

    def forward(self, x):
        # [B, S, D]
        output_forward = self.mamba_forward(x)
        output_forward = self.addnorm_for(output_forward, x)

        temp = output_forward
        output = self.ffn(output_forward.transpose(-1, 1)).transpose(-1, 1)
        output = self.addnorm_ffn(output, temp)
        return output

class EncoderLayer(nn.Module):
    def __init__(self, mamba_forward, mamba_backward, d_model=128, d_ff=256, dropout=0.2, 
                 activation="relu", bi_dir=0, residual=1):
        super(EncoderLayer, self).__init__()
        self.bi_dir = bi_dir
        self.mamba_forward = mamba_forward
        self.residual = residual
        self.addnorm_for = Add_Norm(d_model, dropout, residual, drop_flag=0)

        if self.bi_dir:
            self.mamba_backward = mamba_backward
            self.addnorm_back = Add_Norm(d_model, dropout, residual, drop_flag=0)
        
        self.ffn = nn.Sequential(
            nn.Conv1d(in_channels=d_model, out_channels=d_ff, kernel_size=1),
            nn.ReLU() if activation == "relu" else nn.GELU(),
            nn.Dropout(dropout),
            nn.Conv1d(in_channels=d_ff, out_channels=d_model, kernel_size=1)
        )
        self.addnorm_ffn = Add_Norm(d_model, dropout, residual, drop_flag=1)

    def forward(self, x):
        # [B, S, D]
        output_forward = self.mamba_forward(x)
        output_forward = self.addnorm_for(output_forward, x)

        if self.bi_dir:
            output_backward = self.mamba_backward(x.flip(dims=[1])).flip(dims=[1])
            output_backward = self.addnorm_back(output_backward, x)
            output = output_forward + output_backward
        else:
            output = self.addnorm_for(output_forward, x)
        temp = output
        output = self.ffn(output.transpose(-1, 1)).transpose(-1, 1)
        output = self.addnorm_ffn(output, temp)
        return output
class tsEncoderLayer(nn.Module):
    def __init__(self, mamba_forward, mamba_backward, d_model=128, sp_d_model=128, d_ff=256, dropout=0.2, 
                 activation="relu", bi_dir=0, residual=1):
        super(tsEncoderLayer, self).__init__()
        self.bi_dir = bi_dir
        self.mamba_forward = mamba_forward
        self.residual = residual
        self.addnorm_for = Add_Norm( d_model, dropout, residual, drop_flag=0)

        if self.bi_dir:
            self.mamba_backward = mamba_backward
            self.addnorm_back = Add_Norm(sp_d_model, dropout, residual, drop_flag=0)
        
        self.ffn = nn.Sequential(
            nn.Conv1d(in_channels=d_model, out_channels=d_ff, kernel_size=1),
            nn.ReLU() if activation == "relu" else nn.GELU(),
            nn.Dropout(dropout),
            nn.Conv1d(in_channels=d_ff, out_channels=d_model, kernel_size=1)
        )
        self.addnorm_ffn = Add_Norm(d_model, dropout, residual, drop_flag=1)

    def forward(self, x):
        # [B, S, D]
        output_forward = self.mamba_forward(x)
        output_forward = self.addnorm_for(output_forward, x)

        if self.bi_dir:
            x = x.transpose(1, 2)
            # print(f"x:{x.shape}")
            output_backward = self.mamba_backward(x)
            output_backward = self.addnorm_back(output_backward, x).transpose(1, 2)
            # print(f"output_forward:{output_forward.shape}output_backward:{output_backward.shape}")
            output = output_forward + output_backward
        else:
            output = output_forward
        temp = output
        output = self.ffn(output.transpose(-1, 1)).transpose(-1, 1)
        output = self.addnorm_ffn(output, temp)
        return output

class Encoder(nn.Module):
    def __init__(self, mamba_layers, norm_layer=None):
        super(Encoder, self).__init__()
        self.mamba_layers = nn.ModuleList(mamba_layers)
        self.norm = norm_layer

    def forward(self, x):
        # [B, S, D]
        for mamba_block in self.mamba_layers:
            x = mamba_block(x)

        if self.norm is not None:
            x = self.norm(x)

        return x
