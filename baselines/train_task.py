#!/usr/bin/env python
# TODO: turn this into a script which can train any of the tasks given 
# a command line argument
import argparse
import os

import torch.nn as nn
from torch.utils.data import DataLoader

import mdtk.pytorch_models
import mdtk.pytorch_trainers
from mdtk.pytorch_datasets import transform_to_torchtensor
from mdtk.formatters import CommandVocab, FORMATTERS, create_corpus_csvs


def parse_args():
    parser = argparse.ArgumentParser()

    # Filepath stuff
    parser.add_argument("-i", "--input", default='acme', help='The '
                        'base directory of the ACME dataset to use as input.')
    parser.add_argument("-o", "--output", required=False, type=str,
                        help="Directory and prefix to which to save model outputs. "
                        "e.g.: output/model.checkpoint",
                        default=os.path.join('.', 'model.checkpoint'))

    # Basic task setup args
    parser.add_argument("--format", required=False, choices=FORMATTERS.keys(),
                        help='The format to use as input to the model. If the '
                        'format-specific csvs have not yet been created, this '
                        'will create them. Choices are '
                        f'{list(FORMATTERS.keys())}. Required if --baseline '
                        'is not given.')

    parser.add_argument("--task", required=True, choices=range(1, 5), help='The '
                        'task number to train a model for.', type=int)

    parser.add_argument("--baseline", action='store_true', help='Ignore all '
                        'arguments (besides --input and --output) and run the '
                        'baseline model for the given --task.')

    # Network structure args
    parser.add_argument("-hs", "--hidden", type=int, default=100,
                        help="Hidden size of the model LSTM layers of the model.")
    parser.add_argument("-d", "--dropout", type=float, default=0.1,
                        help="Dropout to use.")
    parser.add_argument("-s", "--seq_len", type=int, default=250,
                        help="maximum sequence length.")
    parser.add_argument("--embedding", type=int, default=128,
                        help="Size of embedding vector. (--format command only)")
    parser.add_argument("--layers", type=int, default=[], nargs='*',
                        help='Size of linear (post-LSTM) layers. '
                        '(--format pianoroll only)')

    # Training/DataLoading args
    parser.add_argument("-b", "--batch_size", type=int, default=64,
                        help="number of batch_size")
    parser.add_argument("-e", "--epochs", type=int, default=1000,
                        help="number of epochs")
    parser.add_argument("-w", "--num_workers", type=int, default=4,
                        help="dataloader worker size")
    parser.add_argument("--with_cpu", action='store_true', default=False,
                        help="Train with CPU, default is to try and use CUDA. "
                        "A warning will be thrown if CUDA is not available, "
                        "and CPU used in that case.")
    parser.add_argument("--cuda_devices", type=int, nargs='+',
                        default=None, help="CUDA device ids")
    parser.add_argument("--batch_log_freq", default='10',
                        help="printing loss every n batches: setting to None "
                        "means no logging.")
    parser.add_argument("--epoch_log_freq", default='1',
                        help="printing loss every n epochs: setting to None "
                        "means no logging.")
    parser.add_argument("--in_memory", type=bool, default=True,
                        help="Loading on memory: true or false")

    # Optimizer args
    parser.add_argument("--lr", type=float, default=1e-4,
                        help="learning rate of adam")
    parser.add_argument("--weight_decay", type=float, default=0.01,
                        help="weight_decay of adam")
    parser.add_argument("--b1", "--adam_beta1", type=float, default=0.9,
                        help="adam first beta value")
    parser.add_argument("--b2", "--adam_beta2", type=float, default=0.999,
                        help="adam first beta value")

    # Piano-roll specific size args
    parser.add_argument("--pr-min-pitch", type=int, default=21,
                        help="Minimum pianoroll pitch")
    parser.add_argument("--pr-max-pitch", type=int, default=108,
                        help="Maximum pianoroll pitch")

    args = parser.parse_args()
    return args



task_names = [
    'ErrorDetection',
    'ErrorClassification',
    'ErrorIdentification',
    'ErrorCorrection'
]

task_trainers = [
    getattr(mdtk.pytorch_trainers, f'{task_name}Trainer')
    for task_name in task_names
]

task_criteria = [
    nn.CrossEntropyLoss(),
    nn.CrossEntropyLoss(),
    nn.CrossEntropyLoss(),
    nn.BCEWithLogitsLoss(reduction='mean')
]



if __name__ == '__main__':
    args = parse_args()
    
    if args.baseline:
        # Setup args for the baseline for args.task
        raise NotImplementedError(f"Baseline not created for task {args.task} yet.")
    else:
        assert args.format is not None, (
            '--format is a required argument if --baseline is not given.'
        )
        
    
    if os.path.split(args.output)[0]:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)

    # Generate (if needed) and load formatted csv
    prefix = FORMATTERS[args.format]["prefix"]
    if not all([os.path.exists(
            os.path.join(args.input, f'{split}_{prefix}_corpus.csv')
        ) for split in ['train', 'valid', 'test']]):
        create_corpus_csvs(args.input, FORMATTERS[args.format])
    train_dataset = os.path.join(args.input, f'train_{prefix}_corpus.csv')
    valid_dataset = os.path.join(args.input, f'valid_{prefix}_corpus.csv')
    test_dataset = os.path.join(args.input, f'test_{prefix}_corpus.csv')
    
    task_idx = args.task - 1
    task_name = task_names[task_idx]
    model_name = FORMATTERS[args.format]['models'][task_idx]
    if model_name is None:
        raise NotImplementedError(f"No model implemented for task {task_name} "
                                  f"with format {args.format}")
    Model = getattr(mdtk.pytorch_models, model_name)
    Dataset = getattr(mdtk.pytorch_datasets, FORMATTERS[args.format]['dataset'])
    Trainer = task_trainers[task_idx]
    Criterion = task_criteria[task_idx]
    
    if args.format == 'command':
        vocab = CommandVocab()
        vocab_size = len(vocab)
        dataset_args = [vocab, args.seq_len]
        dataset_kwargs = {
        }
        model_args = []
        model_kwargs = {
            'vocab_size': vocab_size,
            'embedding_dim': args.embedding,
            'hidden_dim': args.hidden,
            'output_size': 2 if args.task == 1 else 9,
            'dropout_prob': args.dropout
        }
    elif args.format == 'pianoroll':
        dataset_args = [args.seq_len]
        dataset_kwargs = {
            'min_pitch': args.pr_min_pitch,
            'max_pitch': args.pr_max_pitch
        }
        model_args = []
        model_kwargs = {
            'input_dim': 2 * (args.pr_max_pitch - args.pr_min_pitch + 1),
            'hidden_dim': args.hidden,
            'output_dim': 2 if args.task in [1, 3] else 9,
            'layers': args.layers,
            'dropout_prob': args.dropout
        }
        if args.task == 4:
            model_kwargs['output_dim'] = model_kwargs['input_dim']
        

    print(f"Loading train {Dataset.__name__} from {train_dataset}")
    train_dataset = Dataset(train_dataset, *dataset_args, **dataset_kwargs,
                            in_memory=args.in_memory,
                            transform=transform_to_torchtensor)

    print(f"Loading validation {Dataset.__name__} from {valid_dataset}")
    valid_dataset = Dataset(valid_dataset, *dataset_args, **dataset_kwargs,
                            in_memory=args.in_memory,
                            transform=transform_to_torchtensor)

    print(f"Loading test {Dataset.__name__} from {test_dataset}")
    test_dataset = Dataset(test_dataset, *dataset_args, **dataset_kwargs,
                           in_memory=args.in_memory,
                           transform=transform_to_torchtensor)

    print(f"Creating train, valid, and test DataLoaders")
    train_dataloader = DataLoader(train_dataset, batch_size=args.batch_size,
                                  num_workers=args.num_workers, shuffle=True)
    valid_dataloader = DataLoader(valid_dataset, batch_size=args.batch_size,
                                  num_workers=args.num_workers)
    test_dataloader = DataLoader(test_dataset, batch_size=args.batch_size,
                                 num_workers=args.num_workers)
    
    print(f"Building {Model.__name__}")
    model = Model(*model_args, **model_kwargs)
    
    print(f"Using {Criterion.__str__()} as loss function")
    
    if args.batch_log_freq.lower() == 'none':
        batch_log_freq = None
    else:
        batch_log_freq = int(args.batch_log_freq)
    if args.epoch_log_freq.lower() == 'none':
        epoch_log_freq = None
    else:
        epoch_log_freq = int(args.epoch_log_freq)
        
    print("Creating Trainer")
    # TODO: perhaps add a valid_dataloader option and make only function
    #       of test dataloader to be printing the final test loss post
    #       train. Low prio and argument this shouldn't be done (test set
    #       should rarely be viewed, so should be accessed once in blue
    #       moon...not at the end of each training session!)
    with_cuda = not args.with_cpu
    trainer = Trainer(
        model=model,
        criterion=Criterion,
        train_dataloader=train_dataloader,
        test_dataloader=valid_dataloader,
        lr=args.lr,
        betas=(args.b1, args.b2),
        weight_decay=args.weight_decay,
        with_cuda=with_cuda,
        batch_log_freq=batch_log_freq,
        epoch_log_freq=epoch_log_freq,
        formatter=FORMATTERS[args.format]
    )
    
    print("Training Start")
    print(f"Running {args.epochs} epochs")
    # TODO: implement early stopping in Trainers
    # TODO: implement a catch for ctrl+c in Trainers which saves current mdl
    for epoch in range(args.epochs):
        # I test before train as then both train and test values are using
        # the same set of parameters for the same epoch number
        if test_dataloader is not None:
            trainer.test(epoch)
        
        trainer.train(epoch)
        trainer.save(epoch, args.output)