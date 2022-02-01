import matplotlib
matplotlib.use('agg')
from pylab import *
from sklearn.preprocessing import binarize
from sklearn.metrics import precision_score, recall_score, accuracy_score, f1_score, roc_auc_score
from sklearn import linear_model
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
import cPickle as pickle
import os, struct
from array import array as pyarray
from numpy import zeros, random, concatenate, copy, array, delete, int8
from PIL import Image
import pandas as pd

def normlization(image):
    '''divide each element of a image by 255, if its scale is in [0,255]'''
    im = image/255.0
    return im


# def age_filter(data):
#     '''remove certain data points by certain property'''
#
#     return data_new


def c2b(train, generated, adj):
    '''Set the number of 1 in generated data as multiple time of in training data, the rest is set to 0 (or not)'''

    if count_nonzero(generated) <= count_nonzero(train): # special case: number of 1 in generated is <= train, all nonzero in train = 1
        putmask(generated, generated > 0, 1.0)
        return generated

    p = float(count_nonzero(train))/train.size # percentage of nonzero elements
    g = sorted(generated.flatten(), reverse=True)
    idx = int(around(adj*p*len(g))) # with adjustment
    v = g[idx] # any value large than this set to 1, o.w. to 0
    putmask(generated, generated<=v, 0.0) # due to the property of putmask, must first set 0 then set 1
    putmask(generated, generated>v, 1.0)
    print("Nonzero element portion in training data and adjustment value are:")
    print(p, adj)
    print("Nonzero element portion in generated data after adjustment of c2b function:")
    print(float(count_nonzero(generated))/generated.size)
    return generated


def c2bcolwise(train, generated, adj):
    '''Set the number of 1 in each column in generated data the same as the same column in training data, the rest is set to 0.
    Network learn the joint distribution p(x1,...xd), then it should also learn the marginal distribution p(x1),...,p(xd), which
    is approximately the frequent of 1 (and 0) in each feature (coordinate) x1...xd, hence it make sense to do so. But
    by doing so we "force" the generated data have the same portion of 1 in each feature (coordinate) no matter how the network
    is trained (even not trained at all), this doesn't matters since features (coordinates) are dependent, p(x1,...xd) != p(x1)*...*p(xd)
    only setting the frequency of 1 in each feature (coordinate) is not enough, it also relies on the training of NN to learn the
    dependency among features (coordinates), i.e. conditional probability of x1...xd'''
    generated_new = [] # store new one
    s = train.sum(axis=0)
    print('Nonzero element in each feature (coordinate) in training data: ')
    print(list(map(int, s))) # not in scientific notation
    print("Adjustment value is: " + str(adj))
    for col in range(len(s)):
        col_train = train[:,col]
        col_generated = generated[:,col]
        if count_nonzero(col_generated) <= count_nonzero(col_train): # special case: number of 1 in generated is <= train, all nonzero in train = 1
            putmask(col_generated, generated > 0, 1.0)
            generated_new.append(col_generated)
            continue
        g = sorted(col_generated, reverse=True)
        idx = int(adj*s[col]) # with adjustment
        v = g[idx]
        putmask(col_generated, col_generated<=v, 0.0)
        putmask(col_generated, col_generated>v, 1.0)
        generated_new.append(col_generated)
    generated_new = array(generated_new).T
    print('Nonzero element in each feature (coordinate) in generated data: ')
    print(list(map(int, generated_new.sum(axis=0))))
    print('Portion of element that is match between training data and generated data')
    print(float(sum(train == generated_new))/(train.shape[0]*train.shape[1]))
    return generated_new


def select_code(data, top):
    '''select top "top" of feature (by frequency) appears in data (binarized) and remove data (in row) that don't have at least one of these features'''
    s = data.sum(axis=0) # count frequency of each feature, amax(s): 6193, amin(s): 0
    a = array(range(len(s))) # index
    c = [x for _, x in sorted(zip(s, a), reverse=True)][:top]  # c contains indices correspondent to top ICD9 codes, is sorted according to frequency (from largest to smallest)
    a = zeros(len(s))
    a[c] = 1 # to one hot vector, a vector whose indices in c are 1 and all the other are 0
    data_selected = []  # store selected data
    for i in range(len(data)):
        if dot(data[i], a) == 0:  # if dot product is 0, this means the data vector don't have at least one of these features
            pass
        else:
            data_selected.append(data[i])
    return sorted(c), array(data_selected) # index sorted in increasing order: since it is index, should be in increasing order


def data_readf(top):
    '''Read MIMIC-III data'''
    with open('/home/xieliyan/Dropbox/GPU/Data/MIMIC-III/patient_vectors_1071.pickle', 'rb') as f: # Original MIMIC-III data is in GPU1
        MIMIC_ICD9 = pickle.load(f) # dictionary, each one is a list
    MIMIC_data = []
    for value in MIMIC_ICD9: # dictionary to numpy array
        if mean(value) == 0.0: # skip all zero vectors, each patiens should have as least one disease of course
            continue
        MIMIC_data.append(value) # amax(MIMIC_data): 540
    # MIMIC_data = age_filter(MIMIC_data) # remove those patients with age 18 or younger
    # MIMIC_data = binarize(array(MIMIC_data)) # binarize, non zero -> 1, average(MIMIC_data): , type(MIMIC_data[][]): <type 'numpy.int64'>
    # index, MIMIC_data = select_code(MIMIC_data, top) # should be done after binarize because we consider the frequency among different patients, select top codes and remove the patients that don't have at least one of these codes, see "applying deep learning to icd-9 multi-label classification from medical records"
    # MIMIC_data = MIMIC_data[:, index] # keep only those coordinates (features) correspondent to top ICD9 codes
    num_data = (array(MIMIC_data).shape)[0] # data number
    dim_data = (array(MIMIC_data).shape)[1] # data dimension
    return array(MIMIC_data), num_data, dim_data # (46520, 942) 46520 942 for whole dataset

# MIMIC_data, num_data, dim_data = data_readf(top)
# print MIMIC_data.shape, num_data, dim_data


def load_MIMICIII(dataType, _VALIDATION_RATIO, top):
    MIMIC_data, num_data, dim_data = data_readf(top)
    if dataType == 'binary':
        MIMIC_data = clip(MIMIC_data, 0, 1)
    trainX, testX = train_test_split(MIMIC_data, test_size=_VALIDATION_RATIO, random_state=0)
    return trainX, testX, dim_data

# trainX, testX, num_data, dim_data = load_MIMICIII()
# print trainX.shape, testX.shape, num_data, dim_data


def split(matrix, col):
    '''split matrix into feature and target (col th column of matrix), matrix \in R^{N*D}, f_r \in R^{N*(D-1)} , t_r \in R^{N*1}'''
    t_r = matrix[:,col] # shape: (len(t_r),)
    f_r = delete(matrix, col, 1)
    return f_r, t_r


def match(l1,l2):
    '''# count the matched position in 2 lists'''
    if len(l1) != len(l2):
        raise Exception('Two lists must have same length!')
    count = 0
    for i in range(len(l1)):
        if l1[i] == l2[i]:
            count = count + 1
    return count


def dwp(r, g, te, db=0.5, C=1.0):
    '''Dimension-wise prediction & dimension-wise probability, r for real, g for generated, t for test, all without separated feature and target, all are numpy array'''
    rv_pre = []
    gv_pre = []
    rv_pro = []
    gv_pro = []
    for i in range(len(r[0])):
        print(i)
        f_r, t_r = split(r, i) # separate feature and target
        f_g, t_g = split(g, i)
        f_te, t_te = split(te, i) # these 6 are all numpy array
        t_g[t_g < db ] = 0  # hard decision boundary
        t_g[t_g >= db ] = 1
        if (unique(t_r).size == 1) or (unique(t_g).size == 1): # if only those coordinates correspondent to top codes are kept, no coordinate should be skipped, if those patients that doesn't contain top ICD9 codes were removed, more coordinates will be skipped
            print("skip this coordinate")
            continue
        model_r = linear_model.LogisticRegression(C=C) # logistic regression, if labels are all 0, this will cause: ValueError: This solver needs samples of at least 2 classes in the data, but the data contains only one class: 0
        model_r.fit(f_r, t_r)
        label_r = model_r.predict(f_te)
        model_g = linear_model.LogisticRegression(C=C)
        model_g.fit(f_g, t_g)
        label_g = model_g.predict(f_te)
        # print label_r
        # print mean(model_r.coef_), count_nonzero(model_r.coef_), mean(model_g.coef_), count_nonzero(model_g.coef_) # statistics of classifiers
        # rv.append(match(label_r, t_te)/(len(t_te)+10**(-10))) # simply match
        # gv.append(match(label_g, t_te)/(len(t_te)+10**(-10)))
        rv_pre.append(f1_score(t_te, label_r)) # F1 score
        gv_pre.append(f1_score(t_te, label_g))
        # reg = linear_model.LinearRegression() # least square error
        # reg.fit(f_r, t_r)
        # target_r = reg.predict(f_te)
        # reg = linear_model.LinearRegression()
        # reg.fit(f_g, t_g)
        # target_g = reg.predict(f_te)
        # rv.append(square(linalg.norm(target_r-t_te)))
        # gv.append(square(linalg.norm(target_g-t_te)))
        rv_pro.append(float(count_nonzero(t_r))/len(t_r))  # dimension-wise probability, see "https://onlinecourses.science.psu.edu/stat504/node/28"
        gv_pro.append(float(count_nonzero(t_g))/len(t_g))

    return rv_pre, gv_pre, rv_pro, gv_pro


# rv_pre, gv_pre, rv_pro, gv_pro = dwp(r, g, te)

# # test dwp using MIMIC-III data
# trainX, testX, _ = load_MIMICIII('binary', 0.25, 1071)  # load whole dataset and split into training and testing set
# rv_pre, gv_pre, rv_pro, gv_pro = dwp(trainX, trainX, testX)
# plt.scatter(rv_pre, gv_pre)
# plt.title('Dimension-wise prediction, lr')
# plt.xlabel('Real data')
# plt.ylabel('Generated data')
# plt.savefig('./dwp_pre.jpg')
# plt.close()
# plt.scatter(rv_pro, gv_pro)
# plt.title('Dimension-wise probability, lr')
# plt.xlabel('Real data')
# plt.ylabel('Generated data')
# plt.savefig('./dwp_pro.jpg')
# plt.close()

# # detect the special case of f1 score, all 1 (perfect classification) and all 0
# for i in range(20):
#     trainX, testX, _ = load_MIMICIII(dataType, _VALIDATION_RATIO, top)  # load whole dataset and split into training and testing set
#     print trainX.shape, testX.shape
#     rv, gv = dwp(trainX, trainX, testX)
#     rg11 = 0 # both have F1 score equal to 1
#     rg00 = 0 # both have F1 score equal to 0
#     for i in range(len(rv)):
#         if rv[i] == 1 and gv[i] == 1:
#             rg11 = rg11 + 1
#         elif rv[i] == 0 and gv[i] == 0:
#             rg00 = rg00 + 1
#         else:
#             pass
#     print "we need to print out something"
#     print rg11 # 12
#     print rg00 # 52

# # cross validation on C
# for j in range(10):
#     C = 10 ** (-5) * 10 ** (j)
#     for i in range(10):
#         trainX, testX, _ = load_MIMICIII(dataType, _VALIDATION_RATIO, top)  # load whole dataset and split into training and testing set
#         rv, gv = dwp(trainX, trainX, testX, C)
#         print rv
#         plt.close()
#         plt.hist(rv, 10, facecolor='red', alpha=0.5)
#         plt.savefig('./result/genefinalfig/'+str(j)+str(i)+'Histogram.jpg')


def splitbycol(dataType, _VALIDATION_RATIO, col, MIMIC_data):
    '''Separate training and testing for each dimension (col), if we fix column col as label,
    we need to take _VALIDATION_RATIO of data with label 1 and _VALIDATION_RATIO of data with label 0
    and merge them together as testing set and leave the rest. Then balance the rest as training set
    by keeping whomever (0 or 1) is smaller and random select same number from the other one.
    Finally return training and testing set'''
    if dataType == 'binary':
        MIMIC_data = clip(MIMIC_data, 0, 1)
    _, c = split(MIMIC_data, col) # get column col
    if (unique(c).size == 1): # skip column: only one class
        return [], []
    MIMIC_data_1 = MIMIC_data[nonzero(c), :][0]  # Separate data matrix by label, label==1
    MIMIC_data_0 = MIMIC_data[where(c == 0)[0], :]
    trainX_1, testX_1 = train_test_split(MIMIC_data_1, test_size=_VALIDATION_RATIO, random_state=0)
    trainX_0, testX_0 = train_test_split(MIMIC_data_0, test_size=_VALIDATION_RATIO, random_state=0)
    testX = concatenate((testX_1, testX_0), axis=0)
    if len(trainX_1) == len(trainX_0):
        trainX = concatenate((trainX_1, trainX_0), axis=0)
    elif len(trainX_1) < len(trainX_0):
        temp_train, temp_test = train_test_split(trainX_0, test_size=len(trainX_1), random_state=0)
        trainX = concatenate((trainX_1, temp_test), axis=0)
        # testX = concatenate((testX, temp_train), axis=0) # can't merge, test set is already done
    else:
        temp_train, temp_test = train_test_split(trainX_1, test_size=len(trainX_0), random_state=0)
        trainX = concatenate((trainX_0, temp_test), axis=0)
        # testX = concatenate((testX, temp_train), axis=0)
    if ((array(trainX).shape)[0] == 0 or (array(testX).shape)[0] == 0): # skip column: no data point in training or testing set
        return [], []
    return trainX, testX # <type 'numpy.ndarray'> <type 'numpy.ndarray'>


def gene_check(col, x_gene):
    '''check if each column (coordinate) has one class or not, balance the data set then output'''
    _, c = split(x_gene, col)  # get column col
    if (unique(c).size == 1):  # skip column: only one class
        return []
    x_gene_1 = x_gene[nonzero(c), :][0]
    x_gene_0 = x_gene[where(c == 0)[0], :]
    if len(x_gene_1) == len(x_gene_0):
        geneX = x_gene
    elif len(x_gene_1) < len(x_gene_0):
        temp_train, temp_test = train_test_split(x_gene_0, test_size=len(x_gene_1), random_state=0)
        geneX = concatenate((x_gene_1, temp_test), axis=0)
    else:
        temp_train, temp_test = train_test_split(x_gene_1, test_size=len(x_gene_0), random_state=0)
        geneX = concatenate((x_gene_0, temp_test), axis=0)
    if (array(geneX).shape)[0] == 0:
        return []
    return x_gene


def statistics(r, g, te, col):
    '''Column specific statistics (precision, recall(Sensitivity), f1-score, AUC)'''
    f_r, t_r = split(r, col)  # separate feature and target
    f_g, t_g = split(g, col)
    f_te, t_te = split(te, col)  # these 6 parts are all numpy array
    # t_g[t_g < 1.0] = 0  # hard decision boundary
    # t_g[t_g >= 0.5] = 1
    if (unique(t_r).size == 1) or (unique(t_g).size == 1):  # if only those coordinates correspondent to top codes are kept, no coordinate should be skipped, if those patients that doesn't contain top ICD9 codes were removed, more coordinates will be skipped
        return [], [], [], [], [], [], [], []
    model_r = linear_model.LogisticRegression()  # logistic regression, if labels are all 0, this will cause: ValueError: This solver needs samples of at least 2 classes in the data, but the data contains only one class: 0
    model_r.fit(f_r, t_r)
    label_r = model_r.predict(f_te) # decision boundary is 0
    model_g = linear_model.LogisticRegression()
    model_g.fit(f_g, t_g)
    label_g = model_r.predict(f_te)
    precision_r = precision_score(t_te, label_r) # precision
    precision_g = precision_score(t_te, label_g)
    recall_r = recall_score(t_te, label_r) # recall
    recall_g = recall_score(t_te, label_g)
    acc_r = accuracy_score(t_te, label_r) # accuracy
    acc_g = accuracy_score(t_te, label_g)
    f1score_r = f1_score(t_te, label_r)  # f1-score
    f1score_g = f1_score(t_te, label_g)
    auc_r = roc_auc_score(t_te, label_r) # AUC
    auc_g = roc_auc_score(t_te, label_g)

    return precision_r, precision_g, recall_r, recall_g, acc_r, acc_g, f1score_r, f1score_g, auc_r, auc_g


# # test statistics using splitbycol
# dataType = 'binary'
# _VALIDATION_RATIO = 0.25
# precision_r_all = []
# precision_g_all = []
# recall_r_all = []
# recall_g_all = []
# acc_r_all = []
# acc_g_all = []
# f1score_r_all = []
# f1score_g_all = []
# auc_r_all = []
# auc_g_all = []
#
# top = 1071 # dummy
# MIMIC_data, _, dim_data = data_readf(top)
# for col in range(dim_data):
#     print col
#     trainX, testX = splitbycol(dataType, _VALIDATION_RATIO, col, MIMIC_data)
#     if trainX == []:
#         print "skip this coordinate"
#         continue
#     precision_r, precision_g, recall_r, recall_g, acc_r, acc_g, f1score_r, f1score_g, auc_r, auc_g = statistics(trainX, trainX, testX, col)
#     if precision_r == []:
#         print "skip this coordinate"
#         continue
#     precision_r_all.append(precision_r)
#     precision_g_all.append(precision_g)
#     recall_r_all.append(recall_r)
#     recall_g_all.append(recall_g)
#     acc_r_all.append(acc_r)
#     acc_g_all.append(acc_g)
#     f1score_r_all.append(f1score_r)
#     f1score_g_all.append(f1score_g)
#     auc_r_all.append(auc_r)
#     auc_g_all.append(auc_g)
# bins = 100
# plt.hist(precision_r_all, bins, facecolor='red', alpha=0.5)
# plt.title('Histogram of precision on each dimension of training data, lr')
# plt.xlabel('Precision (total number: ' + str(len(precision_r_all)) + ' )')
# plt.ylabel('Frequency')
# plt.savefig('./result/genefinalfig/hist_precision_r.jpg')
# plt.close()
# plt.hist(precision_g_all, bins, facecolor='red', alpha=0.5)
# plt.title('Histogram of precision on each dimension of generated data, lr')
# plt.xlabel('Precision (total number: ' + str(len(precision_r_all)) + ' )')
# plt.ylabel('Frequency')
# plt.savefig('./result/genefinalfig/hist_precision_g.jpg')
# plt.close()
# plt.hist(recall_r_all, bins, facecolor='red', alpha=0.5)
# plt.title('Histogram of recall on each dimension of training data, lr')
# plt.xlabel('Recall (total number: ' + str(len(precision_r_all)) + ' )')
# plt.ylabel('Frequency')
# plt.savefig('./result/genefinalfig/hist_recall_r.jpg')
# plt.close()
# plt.hist(recall_g_all, bins, facecolor='red', alpha=0.5)
# plt.title('Histogram of recall on each dimension of generated data, lr')
# plt.xlabel('Recall (total number: ' + str(len(precision_r_all)) + ' )')
# plt.ylabel('Frequency')
# plt.savefig('./result/genefinalfig/hist_recall_g.jpg')
# plt.close()
# plt.hist(acc_r_all, bins, facecolor='red', alpha=0.5)
# plt.title('Histogram of accuracy on each dimension of training data, lr')
# plt.xlabel('Accuracy (total number: ' + str(len(precision_r_all)) + ' )')
# plt.ylabel('Frequency')
# plt.savefig('./result/genefinalfig/hist_acc_r.jpg')
# plt.close()
# plt.hist(acc_g_all, bins, facecolor='red', alpha=0.5)
# plt.title('Histogram of accuracy on each dimension of generated data, lr')
# plt.xlabel('Accuracy (total number: ' + str(len(precision_r_all)) + ' )')
# plt.ylabel('Frequency')
# plt.savefig('./result/genefinalfig/hist_acc_g.jpg')
# plt.close()
# plt.hist(f1score_r_all, bins, facecolor='red', alpha=0.5)
# plt.title('Histogram of f1score on each dimension of training data, lr')
# plt.xlabel('f1score (total number: ' + str(len(precision_r_all)) + ' )')
# plt.ylabel('Frequency')
# plt.savefig('./result/genefinalfig/hist_f1score_r.jpg')
# plt.close()
# plt.hist(f1score_g_all, bins, facecolor='red', alpha=0.5)
# plt.title('Histogram of f1score on each dimension of generated data, lr')
# plt.xlabel('f1score (total number: ' + str(len(precision_r_all)) + ' )')
# plt.ylabel('Frequency')
# plt.savefig('./result/genefinalfig/hist_f1score_g.jpg')
# plt.close()
# plt.hist(auc_r_all, bins, facecolor='red', alpha=0.5)
# plt.title('Histogram of AUC on each dimension of training data, lr')
# plt.xlabel('AUC (total number: ' + str(len(precision_r_all)) + ' )')
# plt.ylabel('Frequency')
# plt.savefig('./result/genefinalfig/hist_AUC_r.jpg')
# plt.close()
# plt.hist(auc_g_all, bins, facecolor='red', alpha=0.5)
# plt.title('Histogram of AUC on each dimension of generated data, lr')
# plt.xlabel('AUC (total number: ' + str(len(precision_r_all)) + ' )')
# plt.ylabel('Frequency')
# plt.savefig('./result/genefinalfig/hist_AUC_g.jpg')
# plt.close()

def fig_add_noise(List):
    '''adding noise to results to make them distinguishable on figure'''
    print(len(List))
    print(0.0001*random.randn(len(List)))
    List_new = List + 0.0001*random.randn(len(List))
    return List_new

# def scale_transform(self, image):
#     '''this function transform the scale of generated image (0, largest pixel value) to (0,255) linearly'''
#     im = array(image)
#     Max = amax(im)
#     for i in range(len(im)):
#         im[i] = (im[i] / Max) * 255
#     return im


# def im_avg(im):
#     '''compress image from rbg to grayscale, input should be numpy array'''
#     return average(im, axis=2).reshape(64,64,1)


def loaddata_face(path):
    # for file in os.listdir(path):
    #     print file
    im_name = array([name for name in os.listdir(path) if os.path.isfile(os.path.join(path, name))])
    N = len(im_name) # count files in directory
    # N = 10
    image_n = zeros(shape=(N, 64, 64, 1)) # normalized image
    for i in range(N):
        jpgfile = Image.open(path + im_name[i])
        # print asarray(jpgfile.getdata(),dtype=float64).shape
        # print jpgfile.size
        # image_n[i] = im_avg(asarray(jpgfile.getdata(),dtype=float64).reshape((jpgfile.size[1],jpgfile.size[0],(asarray(jpgfile.getdata(),dtype=float64).shape)[1])))
        image_n[i] = normlization(asarray(jpgfile.getdata(),dtype=float64).reshape((jpgfile.size[1],jpgfile.size[0],1))) # image is averaged
    return image_n

# path = "./face/CelebA/img_align_celeba_50k_1st_r_64_64_1/"
# im = loaddata_face(path)

# def loaddata_face_batch(dataset, batch_size):
#     '''random select batch from whole dataset'''
#     res = dataset[random.choice(len(dataset), batch_size)]
#     # res = res.reshape((batch_size, 784))  # type(res[0][0]): numpy.float64
#     return res

# batch_size = 2
# res = loaddata_face_batch(im, batch_size)

def Rsample(data, label, bs):
    a = random.choice(len(label), bs, replace=False)
    return data[a], label[a]

def MNIST_c(file_path, data_path, path_output, digit_pair, number_train, iter, C):
    '''classification task to test the quality of generated data of MNIST
    number_train: number of training points from each digit, randomly selected
    number_test: number of testing points from each digit, randomly selected
    iter: time of random selection
    C: Logistic regression's parameter
    test see "test code of MNIST_c" in test.py
    '''
    files = os.listdir(file_path) # contains all digits (all pairs) from all privacy levels
    files_1st = [] # store files correspondent to 1st digit
    files_2nd = []  # store files correspondent to 2nd digit

    for f in files: # select those only from given digit pairs
        if ('x_gene_' + digit_pair[0]) in f:
            files_1st.append(f)
        elif ('x_gene_' + digit_pair[1]) in f:
            files_2nd.append(f)
        else:
            continue

    files_1st.sort()
    files_2nd.sort()
    print(files_1st)
    print(files_2nd)

    data_train_1st, label_train_1st = loaddata(digit_pair[0], 'training', data_path) # type(label_train_1st[0]): numpy.uint8
    data_train_2nd, label_train_2nd = loaddata(digit_pair[1], 'training', data_path)
    data_test_1st, label_test_1st = loaddata(digit_pair[0], 'testing', data_path)
    data_test_2nd, label_test_2nd = loaddata(digit_pair[1], 'testing', data_path)

    data_train_1st = normlization(data_train_1st) # normlization
    data_train_2nd = normlization(data_train_2nd)
    data_test_1st = normlization(data_test_1st)
    data_test_2nd = normlization(data_test_2nd)

    label_train_1st = array([+1] * len(label_train_1st))  # label transformation
    label_train_2nd = array([-1] * len(label_train_2nd))
    label_test_1st = array([+1] * len(label_test_1st))
    label_test_2nd = array([-1] * len(label_test_2nd))

    dict = {} # store all generated data, # of 0: 5923, # of 1: 6742
    for i in range(len(files_1st)):
        with open(file_path + files_1st[i], 'rb') as f:
            data_1st = array(pickle.load(f))
            data_1st = normlization(data_1st)
            dict['data_' + files_1st[i]] = data_1st
        with open(file_path + files_2nd[i], 'rb') as f:
            data_2nd = array(pickle.load(f))
            data_2nd = normlization(data_2nd)
            dict['data_' + files_2nd[i]] = data_2nd
        label_1st = copy(label_train_1st) # create label, in wgan.py, we generate equal number of data as training samples.
        label_2nd = copy(label_train_2nd)
        dict['label_' + files_1st[i]] = array(label_1st)
        dict['label_' + files_2nd[i]] = array(label_2nd)

    accuracy = [] # training and generated
    for i in range(len(files_1st)+1):
        accuracy.append([])

    # testing data
    data_test_s = concatenate((data_test_1st, data_test_2nd), axis=0)  # random select from testing set
    label_test_s = concatenate((label_test_1st, label_test_2nd))

    for i in range(iter):
        print('iter ' + str(i))

        # training data
        a1 = random.choice(len(label_train_1st), number_train, replace=False) # random selection
        data_train_1st_s = data_train_1st[a1]
        label_train_1st_s = label_train_1st[a1]
        a2 = random.choice(len(label_train_2nd), number_train, replace=False)
        data_train_2nd_s = data_train_2nd[a2]
        label_train_2nd_s = label_train_2nd[a2]
        data_train_s = concatenate((data_train_1st_s, data_train_2nd_s), axis=0) # merge 2 digits
        label_train_s = concatenate((label_train_1st_s, label_train_2nd_s))

        # https://towardsdatascience.com/logistic-regression-using-python-sklearn-numpy-mnist-handwriting-recognition-matplotlib-a6b31e2b166a
        logisticRegr = linear_model.LogisticRegression(solver='lbfgs', C=C)
        logisticRegr.fit(data_train_s, label_train_s)
        accuracy[0].append(logisticRegr.score(data_test_s, label_test_s))

        # generated data
        for j in range(len(files_1st)):
            data_1st = dict['data_' + files_1st[j]]
            data_2nd = dict['data_' + files_2nd[j]]
            label_1st = dict['label_' + files_1st[j]]
            label_2nd = dict['label_' + files_2nd[j]]
            data_1st_s = data_1st[a1]
            label_1st_s = label_1st[a1]
            data_2nd_s = data_2nd[a2]
            label_2nd_s = label_2nd[a2]
            data_s = concatenate((data_1st_s, data_2nd_s), axis=0)
            label_s = concatenate((label_1st_s, label_2nd_s))

            logisticRegr = linear_model.LogisticRegression(solver='lbfgs', C=C)
            logisticRegr.fit(data_s, label_s)
            accuracy[j+1].append(logisticRegr.score(data_test_s, label_test_s))

    accuracy[2], accuracy[4] = accuracy[4], accuracy[2] # due to sort, need to exchange
    accuracy[3], accuracy[4] = accuracy[4], accuracy[3]
    with open(path_output + 'datafile/acc.pickle', 'wb') as fp: # store accuracy data
        pickle.dump(accuracy, fp)

    Name = ['Training', 'infty', '11.5', '5.76', '3.2', '0.72'] # epsilon value
    plt.boxplot(accuracy)
    plt.title('Accuracy of classifiers build from training and generated data')
    plt.xlabel(Name)
    plt.ylabel('Accuracy')
    plt.savefig(path_output + 'genefinalfig/Accuracy.png')  # save map with trajectory
    plt.close()

# load data and labels into matrix of specific digit
def loaddata(digits, dataset, path):  # digits should among 0-9, dataset should be 'training' or 'testing', path is where you store your dataset file

    # get the path of dataset
    if dataset is 'training':
        fname_img = os.path.join(path, 'train-images.idx3-ubyte')
        fname_lbl = os.path.join(path, 'train-labels.idx1-ubyte')
    else:
        fname_img = os.path.join(path, 't10k-images.idx3-ubyte')
        fname_lbl = os.path.join(path, 't10k-labels.idx1-ubyte')

    # if this is a label file
    flbl = open(fname_lbl, 'rb')
    magic_nr, size = struct.unpack('>II', flbl.read(8))  # read the header information in the label file, '>II' means using big-endian, read 8 characters.
    lbl = pyarray("b", flbl.read())  # 'b' for signed char
    flbl.close()

    # if this is a image file
    fimg = open(fname_img, 'rb')
    magic_nr, size, rows, cols = struct.unpack(">IIII", fimg.read(16))  # read the header information in the image file.
    img = pyarray('B', fimg.read())  # 'B' for unsigned char
    fimg.close()

    # extract the labels conrresponding to the digits we want
    ind = [k for k in range(size) if str(lbl[k]) in digits]  # list that contain the labels
    N = len(ind)  # number of labels

    # store and return the result
    images = zeros((N, rows * cols), dtype='uint8')
    labels = zeros((N, 1), dtype='uint8')
    for i in range(len(ind)):
        images[i] = array(img[ind[i] * rows * cols: (ind[i] + 1) * rows * cols])  # every row is an image. every row: array([784 data, , , ,...])
        labels[i] = lbl[ind[i]]
    labels = array([v[0] for v in labels]) # array to int

    return images, labels


# images:
# #array([[0, 0, 0, ..., 0, 0, 0],
# #       [0, 0, 0, ..., 0, 0, 0],
# #       [0, 0, 0, ..., 0, 0, 0],
# #       ...,
# #       [0, 0, 0, ..., 0, 0, 0],
# #       [0, 0, 0, ..., 0, 0, 0],
# #       [0, 0, 0, ..., 0, 0, 0]], dtype=uint8)
# the type of each element is not float !
#
# images[0]:
# #array([0, 0, 0, ..., 0, 0, 0], dtype=uint8)
#
# labels:
# #array([[ 1],
# #       [ 1],
# #       [ 1],
# #       ...,
# #       [ 1],
# #       [-1],
# #       [ 1]], dtype=int8)
#
# #labels[1] looks like: array([1], dtype=int8)
# #labels[3] looks like: array([-1], dtype=int8)
# #labels[1]*labels[3] is array([-1], dtype=int8)
# #labels[1]*2 is array([2], dtype=int8)
#
# average norm of MNIST data (scale: 0 to 255) is 2349.74572748