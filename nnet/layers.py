import abc
import numpy as np
from numpy.typing import NDArray
from typing import Tuple

# project imports
from .loss import Loss
from .activation import Activation, Softmax, Linear
from .optimizers import Optimizer, GradientDescent
from .common import PreActivation, MatMul


class Layer(abc.ABC):
    @abc.abstractmethod
    def set_optimizer(self, optimizer: Optimizer) -> None:
        pass

    @abc.abstractmethod
    def forward(self,
                X: NDArray[np.float64],
                training: bool = True) -> NDArray[np.float64]:
        pass

    @abc.abstractmethod
    def backward(self,
                 dY: NDArray[np.float64],
                 batch_size: int,
                 Y: NDArray[np.float64] = None,
                 Y_hat: NDArray[np.float64] = None,
                 loss_function: Loss = None) -> NDArray[np.float64]:
        pass


class Dense(Layer):
    def __init__(self, size: Tuple[int, int], activation: Activation):
        # initialize parameters
        x_size, y_size = size
        self.W = np.random.uniform(-1, 1, (y_size, x_size))
        self.b = np.random.uniform(-1, 1, (y_size,))
        self.activation = activation
        self.optimizer = GradientDescent()

        # initialize cache
        self.X = None
        self.Z = None

    def set_optimizer(self, optimizer):
        self.optimizer = optimizer.get_optimizer(self.W.shape)

    def forward(self, X, training=True):
        # forward propagation
        Z = PreActivation.forward(X, self.W, self.b)
        A = self.activation.forward(Z)

        # cache values for gradient descent
        if training is True:
            self.X = X
            self.Z = Z

        # return activation
        return A

    def backward(self, dY, batch_size, Y=None, Y_hat=None, loss_function=None):
        if loss_function is None or Y is None or Y_hat is None:
            dY = self.activation.backward(self.Z) * dY
        else:
            dY = loss_function.backward(Y, Y_hat, self.activation, self.Z)

        # calculate gradient
        dW, db, dX = PreActivation.backward(dY, self.X, self.W, batch_size)

        # update parameters
        W, b = self.optimizer.update_params(dW, db, self.W, self.b)
        self.W = W
        self.b = b

        return dX  # return derivative of input


class PositionalEncoding(Layer):
    def __init__(self,
                 sequence_len: int,
                 dimension: int,
                 eta: int = 10000,
                 bptt: bool = False):
        temp = np.zeros((sequence_len, dimension))  # initialize positional encodings
        for k in range(sequence_len):
            for i in np.arange(int(dimension / 2)):
                denominator = np.power(eta, 2 * i / dimension)
                temp[k, 2 * i] = np.sin(k / denominator)
                temp[k, 2 * i + 1] = np.cos(k / denominator)

        self.dimension = dimension
        self.pos_encoding = temp  # cache positional encodings
        self.bptt = bptt  # set true if the next layer is attention

    def set_optimizer(self, optimizer):
        pass

    def get_positional_encoding(self):
        return self.pos_encoding

    def forward(self, X, training=True):
        encoded = []
        for input_seq in X.T:
            encoded.append(input_seq + self.pos_encoding)  # add positional encoding to each input sequences

        if self.bptt is False:
            return np.array(encoded)  # size of (batch_size, sequence_length, dimensions)
        else:
            return np.array(encoded).reshape((-1, self.dimension)).T  # size of (dimension, sample_size)

    def backward(self, dY, batch_size, Y=None, Y_hat=None, loss_function=None):
        return dY


class SelfAttention(Layer):
    def __init__(self,
                 sequence_len: int,
                 dimension: int,
                 embedding: bool = True,
                 bptt: bool = True):
        self.embedding = embedding  # set the if the attention layer requires embedding

        # when requires embedding prepare linear layers
        if embedding is True:
            self.query = Dense((dimension, dimension), Linear())
            self.key = Dense((dimension, dimension), Linear())
            self.value = Dense((dimension, dimension), Linear())

            # cache values to compute derivatives
            self.query_val = []
            self.key_val = []
            self.value_val = []

        self.sequence_len = sequence_len
        self.dimension = dimension
        self.bptt = bptt
        self.attention_scores = []  # cache scores

    def set_optimizer(self, optimizer):
        pass

    def get_attention_scores(self):
        return np.array(self.attention_scores)

    @staticmethod
    def __attention_derivative(attention: NDArray[np.float64], dY: NDArray[np.float64]):
        dY_hat = []
        for i in range(len(attention)):
            dS = np.reshape(attention[i], (-1, 1))
            dS = np.diagflat(dS) - np.dot(dS, dS.T)
            dY_hat.append(dY[i].dot(dS))

        return np.array(dY_hat)

    def forward(self, X, training=True):
        # reshape input if it is in bptt mode
        if len(X.shape) == 2:
            X = np.reshape(X.T, (-1, self.sequence_len, self.dimension))

        if self.embedding is True:
            flatten_seq = np.reshape(X, (-1, self.dimension))
            query_val = self.query.forward(flatten_seq.T)
            key_val = self.key.forward(flatten_seq.T)
            value_val = self.value.forward(flatten_seq.T)

            self.query_val = np.reshape(query_val.T, (-1, self.sequence_len, self.dimension))
            self.key_val = np.reshape(key_val.T, (-1, self.sequence_len, self.dimension))
            self.value_val = np.reshape(value_val.T, (-1, self.sequence_len, self.dimension))
        else:
            self.query_val = X
            self.key_val = X
            self.value_val = X

        weighted_val = []
        for i in range(len(X)):
            Q, K, V = self.query_val[i], self.key_val[i], self.value_val[i]

            attention_score = MatMul.forward(Q, K.T)
            attention_score = (1 / self.dimension ** 0.5) * attention_score
            attention_score = Softmax.forward(attention_score.T).T
            weighted_val.append(MatMul.forward(attention_score, V))

            self.attention_scores.append(attention_score)  # cache attention scores

        if self.bptt is False:
            return np.array(weighted_val)
        else:
            # reshape the matrix so that (dimension, batch size * sequence length)
            return np.array(weighted_val).reshape((-1, self.dimension)).T

    def backward(self, dY, batch_size, Y=None, Y_hat=None, loss_function=None):
        dY = np.reshape(dY.T, (-1, self.sequence_len, self.dimension))

        Q_grad = []
        K_grad = []
        V_grad = []
        for i in range(len(dY)):
            Q, K, V = self.query_val[i], self.key_val[i], self.value_val[i]
            attention_score = self.attention_scores[i]

            dA, dV = MatMul.backward(dY[i], attention_score, V)
            dA = (1 / self.dimension ** 0.5) * self.__attention_derivative(attention_score, dA)
            dQ, dK = MatMul.backward(dA, Q, K.T)

            Q_grad.append(dQ)
            K_grad.append(dK.T)
            V_grad.append(dV)

        Q_grad = np.array(Q_grad).reshape((-1, self.dimension)).T
        K_grad = np.array(K_grad).reshape((-1, self.dimension)).T
        V_grad = np.array(V_grad).reshape((-1, self.dimension)).T

        if self.embedding is True:
            return self.query.backward(Q_grad, batch_size) + self.key.backward(K_grad, batch_size) + \
                   self.value.backward(V_grad, batch_size)
        else:
            return Q_grad + K_grad + V_grad


class LayerNormalization(Layer):
    def __init__(self, dimension: int):
        self.dimension = dimension
        self.G = np.ones((dimension, 1))
        self.b = np.zeros((dimension,))
        self.optimizer = GradientDescent()
        self.norm = None
        self.X = None

    def set_optimizer(self, optimizer):
        self.optimizer = optimizer.get_optimizer(self.G.shape)

    @staticmethod
    def __norm_derivative(X: NDArray[np.float64], dY: NDArray[np.float64]):
        N = X.shape[1]
        I = np.eye(N)
        mean = np.mean(X, axis=0)
        std = np.std(X, axis=0)
        epsilon = 10 ** -100

        norm_grad = []
        for i in range(len(X)):
            x = np.reshape(X[i], (N, 1))
            diff = x - mean
            dX = ((N * I - 1) / (N * std + epsilon)) - (diff.dot(diff.T) / (N * std ** 3 + epsilon))
            norm_grad.append(dY[i].dot(dX))

        return np.array(norm_grad).T

    def forward(self, X, training=True):
        mean = np.mean(X, axis=0)
        std = np.std(X, axis=0)
        norm = (X - mean) / (std + 10 ** -100)

        if training is True:
            self.norm = norm
            self.X = X

        return self.G * norm + np.reshape(self.b, (self.dimension, 1))

    def backward(self, dY, batch_size, Y=None, Y_hat=None, loss_function=None):
        dG = 1 / batch_size * np.sum(dY * self.norm, axis=1).reshape((self.dimension, 1))
        db = 1 / batch_size * np.sum(dY, axis=1)

        G, b = self.optimizer.update_params(dG, db, self.G, self.b)
        self.G = G
        self.b = b

        return self.__norm_derivative(self.X.T, dY.T)