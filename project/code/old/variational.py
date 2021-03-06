import numpy as np
import tensorflow as tf
import tensorflow_probability as tfp
tfd = tfp.distributions


def create_weights_and_biases(units_prev, units_next):
    # ========================
    # Weights
    # ========================

    mu_init = tf.initializers.glorot_uniform()
    # mu_init = tf.initializers.random_normal(mean=0., stddev=.1)
    # rho_init = tf.initializers.random_normal(mean=-3., stddev=.1)
    rho_init = tf.initializers.constant(-3)

    #with tf.variable_scope("create_weights_and_biases", reuse=tf.AUTO_REUSE):
    weight_mu = tf.get_variable(name="weight_mu", shape=[units_prev, units_next], initializer=mu_init,trainable=True)
    weight_rho = tf.get_variable(name="weight_rho", shape=[units_prev, units_next], initializer=rho_init,trainable=True)

    # sigma = log(1 + exp(rho))
    weight_sigma = tf.nn.softplus(weight_rho)

    # w = mu + sigma * epsilon
    weight_dist = tfd.Normal(loc=weight_mu, scale=weight_sigma)

    # ========================
    # Biases
    # ========================
    #with tf.variable_scope("create_weights_and_biases", reuse=tf.AUTO_REUSE):
    bias_mu = tf.get_variable(name="bias_mu", shape=[units_next], initializer=mu_init,trainable=True)
    bias_rho = tf.get_variable(name="bias_rho", shape=[units_next], initializer=rho_init,trainable=True)

    # sigma = log(1 + exp(rho))
    bias_sigma = tf.nn.softplus(bias_rho)

    # b = mu + sigma * epsilon
    bias_dist = tfd.Normal(loc=bias_mu, scale=bias_sigma)

    return weight_dist, bias_dist

def variational_dense(inputs,
                  units,
                  name,
                  activation=tf.nn.relu,
                  prior_fn=None,
                  params=None):
    """
    prior_fn(units_prev, units_next) -> tfd.Distribution
    """

    # Reuse the variables in this scope, this is crucial for
    # being able to sample multiple times for the same input
    with tf.variable_scope(name):#, reuse=tf.AUTO_REUSE):
        weight_dist, bias_dist = create_weights_and_biases(
            units_prev=inputs.shape[1],
            units_next=units
        )

        weights = weight_dist.sample()
        biases = bias_dist.sample()

        dense = tf.matmul(inputs, weights) + biases

        if activation is not None:
            dense = activation(dense)

        if prior_fn is None:
            prior = create_gaussian_prior({"mu":0., "sigma":0.})
        else:
            prior = prior_fn(params)

        weight_prior_lp = prior.log_prob(weights)
        bias_prior_lp = prior.log_prob(biases)

        weight_var_post_lp = weight_dist.log_prob(weights)
        bias_var_post_lp = bias_dist.log_prob(biases)

        kl_divergence = tf.reduce_sum(weight_var_post_lp - weight_prior_lp)
        #kl_divergence2 = tf.reduce_sum(weight_prior_lp + bias_prior_lp)
        kl_divergence += tf.reduce_sum(bias_var_post_lp - bias_prior_lp)
        #kl_divergence = kl_divergence1 - kl_divergence2
    return dense, kl_divergence

def create_gaussian_prior(params):
    prior = tfd.Normal(loc=params["mu"], scale=tf.exp(-params["sigma"]))
    return prior

def create_mixture_prior(params):
    prior = tfd.Mixture(
        cat=tfd.Categorical(probs=[params["mix_prop"], 1. - params["mix_prop"]]),
        components=[
            tfd.Normal(loc=0., scale=tf.exp(-params["sigma1"])),
            tfd.Normal(loc=0., scale=tf.exp(-params["sigma2"])),
        ])
    return prior


def ELBO_with_logits(logits, kl_divergences, kl_coeff, labels):
    negative_log_likelihood = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=labels,
                                                                             logits=logits)
    negative_log_likelihood = tf.reduce_sum(negative_log_likelihood)

    kl_divergence = sum(kl_divergences)

    elbo = kl_coeff * kl_divergence + negative_log_likelihood

    return elbo, kl_divergence, negative_log_likelihood

def ELBO_with_Gaussian_prior(predictions_list, kl_divergences, kl_coeff, labels):
    mus = [tf.reshape(predictions, [-1, 2])[:, 0] for predictions in predictions_list]
    sigmas = [tf.nn.softplus(tf.reshape(predictions, [-1, 2])[:, 1]) for predictions in predictions_list]

    neg_log_prob = sum([tf.log(sigma) + tf.square(mu - tf.reshape(labels, [-1])) / tf.square(sigma) for mu, sigma in zip(mus, sigmas)])

    kl_divergence = kl_coeff * sum(kl_divergences)

    elbo = kl_divergence + neg_log_prob

    return elbo, kl_divergence, neg_log_prob

def ELBO_with_MSE(predictions_list, kl_divergences, kl_coeff, labels, sigma=1.):
    negative_log_likelihood = sum([tf.losses.mean_squared_error(predictions=tf.reshape(predictions, [-1, 1]), labels=labels) for predictions in predictions_list]) / (2 * sigma**2) + np.log(sigma)

    kl_divergence = kl_coeff * sum(kl_divergences)

    elbo = kl_coeff * kl_divergence + negative_log_likelihood

    return elbo, kl_divergence, negative_log_likelihood
