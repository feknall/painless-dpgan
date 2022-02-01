import cPickle as pickle
from numpy import load, sqrt, log10, pi, concatenate, where, unique, ceil, dot, reshape, random, float64, exp, newaxis, float, asarray, delete, linspace, clip, load, arange, linalg, argmin, array, random, zeros, fill_diagonal, average, amax, amin, sort, sum
import matplotlib
import matplotlib.pyplot as plt

with open('/home/hamid/PycharmProjects/dpgan/result/datafile/x_gene_1_sigma0.0.pickle', 'rb') as fp:
    x_training_data = array(pickle.load(fp))
print x_training_data.shape
print x_training_data[0].shape
for i in range(0, x_training_data.shape[0], x_training_data.shape[0] / 30):
    print i
    plt.imshow((x_training_data[i]).reshape(28, 28), cmap='gray', interpolation='nearest')
    plt.xticks(())
    plt.yticks(())
    plt.show()