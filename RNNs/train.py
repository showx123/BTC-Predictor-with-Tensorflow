#Reference : https://github.com/hunkim/DeepLearningZeroToAll

import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt
from os import listdir
import datetime
tf.set_random_seed(777)  # for reproducibility

class Model():
    num_input = 1
    num_seq = 100
    num_output = 1
    num_hidden = 2
    learning_rate = 0.01

    label_min = 0
    label_max = 35000

    X = tf.placeholder(tf.float32, [None, num_seq, num_input])
    Y = tf.placeholder(tf.float32, [None, num_output])

    # RNN Model + fully-connected
    cell = tf.contrib.rnn.BasicLSTMCell(num_units=num_hidden, state_is_tuple=True, activation=tf.tanh)
    outputs, _ = tf.nn.dynamic_rnn(cell, X, dtype=tf.float32)
    predict = tf.contrib.layers.fully_connected(outputs[:, -1], num_output,
                                                activation_fn=None)  # use last cell's output
    cost = tf.reduce_sum(tf.square(predict - Y))  # MSE
    optimizer = tf.train.AdamOptimizer(learning_rate).minimize(cost)

    # Accuracy Test
    targets = tf.placeholder(tf.float32, [None, 1])
    predictions = tf.placeholder(tf.float32, [None, 1])
    rmse = tf.sqrt(tf.reduce_mean(tf.square(targets - predictions)))
    mpe = tf.reduce_mean((tf.abs(targets - predictions)) / targets) * 100



'''
min max sacling to 0 ~ 1
if label_min and label_max is passed as parameter, use it for min max scaling

parameter 

- data : numpy array

--------------------
returns 

- Normalized numpy array
- label min and label max
'''
def MinMaxScaler(data, label_pos, label_min=0, label_max=0):
    if label_min == 0 and label_max == 0:
        label_min = np.min(data[:,label_pos])
        label_max = np.max(data[:,label_pos])

        # to avoid divide by zero, add noise
        data = (data - np.min(np.abs(data), axis=0)) / (
                    np.max(np.abs(data), axis=0) - np.min(np.abs(data), axis=0) + 1e-8)
        return (data, label_min, label_max)
    else:
        # to avoid divide by zero, add noise
        data = (data - label_min) / (label_max - label_min + 1e-8)

        return data, label_min, label_max



'''
decode scaled(0~1) predict value to original value

parameter

- predict : decoding target
- min : minimum value for data label
- max : maximum value for data label

------------------
returns 

- ret : decoded value
'''
def decodePredict(predict, min, max):
    ret = predict * (max - min + 1e-8)
    ret = ret + min

    return ret


'''
parameter

- data : numpy array
- num_seq : number of sequence for input data
- pos : index of label in data

------------------
returns 

- x : input dataset 
- y : label dataset
'''
def MakeDataSet(data, num_seq, pos):
    x = []
    y = []

    for i in range(len(data) - num_seq):
        x.append(data[i:i+num_seq])
        y.append([data[i+num_seq][pos]])

    return (x,y)


def load_model(path, sess):
    file_name = "saved_model_epoch_"  # prefix of file name that will be loaded

    print("Do you want to restore your model? (Y/N)")
    ans = input()

    old_epoch = 0  # epoch of restored model.
    saver = tf.train.Saver()


    if (ans == 'y') or (ans == 'Y'):
        num = 0
        model_list = []

        # list all models saved.
        for f in listdir(path):
            if f.find(".ckpt.meta") != -1:
                model_list.append(f.replace(".meta", ''))
                print(str(num + 1) + " - " + model_list[num])
                num += 1

        if num == 0:
            print("No models found")
        else:
            print("Select model by number : ")
            num = int(input())
            saver.restore(sess, path + model_list[num - 1])
            print(model_list[num - 1], "is restored")
            old_epoch = int((model_list[num - 1].replace(file_name, "")).replace(".ckpt", ""))
            print("Restored epoch : ", old_epoch)

    return old_epoch, sess


def up_down_accuracy(target, prediction):
    acc_sum = 0

    for i in range(len(target) - 2):
        if(target[i] < target[i+1]) == (target[i] < prediction[i+1]):
            acc_sum += 1

    return acc_sum / (len(target) - 2)


def train(path):
    data_split_rate = 0.7  # dataset split rate for train data. Others will be test data
    label_pos = 0

    model = Model()

    file_name = "saved_model_epoch_"  # prefix of file name that will be saved
    path = path + "/saved/"  # path of files

    data = np.loadtxt('./data.csv', delimiter=',',usecols=(1), skiprows=1)
    train_len = int(len(data) * data_split_rate)

    if model.num_input == 1:
        data = np.reshape(data, (-1, 1))

    test_data = data[train_len:]
    train_data = data[:train_len]

    # train_data, label_min, label_max = MinMaxScaler(train_data, label_pos)
    # test_data = MinMaxScaler(test_data, label_pos, label_min, label_max)

    train_data, label_min, label_max = MinMaxScaler(train_data, label_pos, label_max=model.label_max)
    test_data, _, __ = MinMaxScaler(test_data, label_pos, label_max=model.label_max)

    train_x, train_y = MakeDataSet(train_data, model.num_seq, label_pos)  # shape = [None, num_seq, num_input]
    test_x, test_y = MakeDataSet(test_data, model.num_seq, label_pos)


    # Add ops to save and restore all the variables.
    saver = tf.train.Saver()

    with tf.Session() as sess:
        init = tf.global_variables_initializer()
        sess.run(init)
        old_epoch, sess = load_model(path, sess)

        print("Input training epoch : ")
        epoch = int(input())

        # Training
        for i in range(epoch):
            _, loss = sess.run([model.optimizer, model.cost], feed_dict={model.X: train_x, model.Y: train_y})
            if ((i + 1) % 50 == 0):
                print("Epoch ", i + 1, " : ", loss)

        print("Train finished in : ",  datetime.datetime.now())

        # Testing
        test_predict = sess.run(model.predict, feed_dict={model.X: test_x})
        rmse_val = sess.run(model.rmse, feed_dict={model.targets: test_y, model.predictions: test_predict})
        mpe_val = sess.run(model.mpe, feed_dict={model.targets: test_y, model.predictions:test_predict })

        print("RMSE for test data : ", rmse_val)
        print("MPE for test data : ", mpe_val)
        # print("UP/Down prediction accuracy : ", up_down_accuracy(test_y, test_predict))

        # Save the variables to disk.
        save_path = saver.save(sess, path + file_name + str(epoch + old_epoch) + ".ckpt")
        print("Models saved in : %s" % save_path)

        #predict(path, data, label_min, label_max)

        # Show test accuracy by matplotlib
        plt.plot(test_y)
        plt.plot(test_predict)
        plt.xlabel("Time")
        plt.ylabel("Price")
        plt.show()


def predict(path, data):
    model = Model()
    label_pos = 0

    if model.num_input == 1:
        data = np.reshape(data, (-1, 1))

    with tf.Session() as sess:
        old_epoch, sess = load_model(path, sess)
        label_min = model.label_min
        label_max = model.label_max

        data_len = len(data)
        x, _, _ = MinMaxScaler(data, label_pos, label_min=label_min, label_max=label_max)
        x, _ = MakeDataSet(x[data_len - model.num_seq - 1:], model.num_seq, label_pos)

        test_predict = sess.run(model.predict, feed_dict={model.X: x})
        print('Prediction')
        print(decodePredict(test_predict, label_min, label_max))