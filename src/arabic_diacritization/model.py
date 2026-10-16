"""Exact BiLSTM-CRF architecture extracted from original engine."""
import torch.nn as nn
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence
from torchcrf import CRF

class BiLSTMCRF(nn.Module):

    def __init__(
        self,
        vocab_size,
        num_labels,
        embedding_dim,
        hidden_dim,
        num_layers,
        dropout,
        pad_idx,
    ):

        super().__init__()


        if hidden_dim % 2 != 0:

            raise ValueError(
                "hidden_dim BiLSTM harus genap."
            )


        hidden_per_direction = (
            hidden_dim // 2
        )


        self.embedding = nn.Embedding(
            num_embeddings=vocab_size,
            embedding_dim=embedding_dim,
            padding_idx=pad_idx,
        )


        self.embedding_dropout = nn.Dropout(
            dropout
        )


        self.bilstm = nn.LSTM(
            input_size=embedding_dim,
            hidden_size=hidden_per_direction,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=(
                dropout
                if num_layers > 1
                else 0.0
            ),
        )


        self.output_dropout = nn.Dropout(
            dropout
        )


        self.classifier = nn.Linear(
            hidden_dim,
            num_labels,
        )


        self.crf = CRF(
            num_tags=num_labels,
            batch_first=True,
        )


    def forward(
        self,
        input_ids,
        lengths,
    ):

        embeddings = self.embedding(
            input_ids
        )


        embeddings = self.embedding_dropout(
            embeddings
        )


        packed = pack_padded_sequence(
            embeddings,
            lengths.cpu(),
            batch_first=True,
            enforce_sorted=False,
        )


        packed_output, _ = self.bilstm(
            packed
        )


        bilstm_output, _ = (
            pad_packed_sequence(
                packed_output,
                batch_first=True,
                total_length=
                    input_ids.size(1),
            )
        )


        bilstm_output = self.output_dropout(
            bilstm_output
        )


        return self.classifier(
            bilstm_output
        )


    def loss(
        self,
        input_ids,
        tags,
        mask,
        lengths,
    ):

        emissions = self.forward(
            input_ids,
            lengths,
        )


        log_likelihood = self.crf(
            emissions,
            tags,
            mask=mask,
            reduction="token_mean",
        )


        return -log_likelihood


    def decode(
        self,
        input_ids,
        mask,
        lengths,
    ):

        emissions = self.forward(
            input_ids,
            lengths,
        )


        return self.crf.decode(
            emissions,
            mask=mask,
        )


