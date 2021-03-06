import numpy as np
import tensorflow as tf
import argparse
import os, tempfile
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split

from prune_weights import prune_weights

from utils import is_valid_file

from baseline import baseline_model_fn
from bayes_mnist import bayes_mnist_model_fn
from dropout_mnist import dropout_mnist_model_fn


models = {
    "baseline": baseline_model_fn,
    "bayes_mnist": bayes_mnist_model_fn,
    "dropout_mnist": dropout_mnist_model_fn
}

def mnist_input_fn(data, labels, num_epochs=600, batch_size=128): #shuffle_samples=5000):
    dataset = tf.data.Dataset.from_tensor_slices((data, labels))
    #dataset = dataset.shuffle(shuffle_samples)
    dataset = dataset.repeat(num_epochs)
    dataset = dataset.map(mnist_parse_fn)
    dataset = dataset.batch(batch_size)

    return dataset


def mnist_parse_fn(data, labels):#shuffle_samples=5000
    return (tf.cast(data, tf.float32)/126., tf.cast(labels, tf.int32))


def run(args):

    config = {
        "training_set_size": 60000,
        "num_epochs": 600,
        "batch_size": 128,
        "pruning_percentile": 98
    }

    #num_batches = config["training_set_size"] * config["num_epochs"] / config["batch_size"]
    num_batches = config["training_set_size"] / config["batch_size"]

    model_fn = models[args.model]

    params={
        "data_format": "channels_last",
        "hidden_units": 800,
        "dropout": 0.5,
        "num_mc_samples": 1,
        "prior": "mixture",
        "sigma": 0.,
        "mu": 0.,
        "mix_prop": 0.25,
        "sigma1": 7.,
        "sigma2": 1.,
        #"kl_coeff": "geometric",
        "kl_coeff_decay_rate": 1,
        "kl_coeff": "uniform",
        "num_batches": num_batches,
        "optimizer": "adam",
        "learning_rate": 1e-3,
        "model_dir": args.model_dir,
    }

    classifier = tf.estimator.Estimator(model_fn=model_fn,
                                        model_dir=args.model_dir,
                                        params=params)


    ((train_data, train_labels),
     (eval_data, eval_labels)) = tf.keras.datasets.mnist.load_data()

    
    #train_data, eval_data, train_labels, eval_labels = train_test_split(train_data, train_labels, test_size=0.1666666, stratify = train_labels)


    if args.is_training:
        print("Beginning training of the {} model!".format(args.model))
        classifier.train(input_fn=lambda:mnist_input_fn(train_data, train_labels, num_epochs=config["num_epochs"]))
        print("Training finished!")

    if args.prune_weights:
        print("Pruning weights with {} percentile.".format(config["pruning_percentile"]))
        pruned_model_dir = prune_weights(args.model_dir, config["pruning_percentile"], plot_hist=False)
        classifier = tf.estimator.Estimator(model_fn=model_fn,
                                            model_dir=pruned_model_dir,
                                            params=params)

    eval_results = classifier.evaluate(input_fn=lambda:mnist_input_fn(eval_data, eval_labels))
    print(eval_results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Bayes By Backprop models')

    parser.add_argument('--model', choices=list(models.keys()), default='baseline',
                    help='The model to train.')
    parser.add_argument('--no_training', action="store_false", dest="is_training", default=True,
                    help='Should we just evaluate?')
    parser.add_argument('--model_dir', type=lambda x: is_valid_file(parser, x), default='/tmp/bayes_by_backprop',
                    help='The model directory.')
    parser.add_argument('--prune_weights', action="store_true", dest="prune_weights", default=False,
                    help='Should we do weight pruning during evaluation.')
    args = parser.parse_args()

    run(args)
