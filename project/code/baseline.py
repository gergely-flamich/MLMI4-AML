import tensorflow as tf
import sonnet as snt

class BaseMNIST(snt.AbstractModule):
    """

    """
    def __init__(self,
                 units,
                 name="base_mnist",
                 dropout=False,
                 **kwargs):

        super(BaseMNIST, self).__init__(name=name)

        self.units = units
        self.dropout = dropout
        self.is_training = True

    def negative_log_likelihood(self, logits, labels):
        negative_log_likelihood = tf.nn.sparse_softmax_cross_entropy_with_logits(
            labels=labels,
            logits=logits)

        return tf.reduce_sum(negative_log_likelihood)

    @property
    def kl_divergence(self):
        self._ensure_is_connected()
        return 0

    def _build(self, inputs):
        # Flatten input
        flatten = snt.BatchFlatten()
        flattened = flatten(inputs)

        if self.dropout:
            flattened = tf.contrib.layers.dropout(inputs=flattened,
                                              keep_prob=0.8,
                                              is_training=self.is_training)

        # First linear layer
        linear_1 = snt.Linear(output_size=self.units)

        dense = linear_1(flattened)
        dense = tf.nn.relu(dense)

        if self.dropout:
            dense = tf.contrib.layers.dropout(inputs=dense,
                                              keep_prob=0.5,
                                              is_training=self.is_training)

        # Second linear layer
        linear_2 = snt.Linear(output_size=self.units)

        dense = linear_2(dense)
        dense = tf.nn.relu(dense)

        if self.dropout:
            dense = tf.contrib.layers.dropout(inputs=dense,
                                              keep_prob=0.8,
                                              is_training=self.is_training)

        # Final linear layer
        linear_out = snt.Linear(output_size=10)

        logits = linear_out(dense)

        self._layers = [linear_1, linear_2, linear_out]

        return logits
