# -*- coding: utf-8 -*-
"""
Created on Wed Nov  7 23:14:11 2018

@author: Nightzsky
"""

from __future__ import print_function
import keras
from keras.datasets import mnist,reuters
from keras.models import Sequential
from keras.layers import Dense, Dropout, Activation
from keras.optimizers import RMSprop
import matplotlib.pyplot as plt
import numpy as np
from keras.preprocessing.text import Tokenizer

#download and load the MNIST dataset
(x_train, y_train), (x_test, y_test) = mnist.load_data()

print(x_train.shape)
print(x_test.shape)

plt.imshow(x_train[20],cmap='gray')
plt.show()

#Some simple preprocessing on the dataset, reshape it from 2D to 1D, convert to float and normalize to between 0-1
x_train = x_train.reshape(60000,784)
x_test = x_test.reshape(10000,784)

x_train = x_train.astype('float32')
x_test = x_test.astype('float32')

x_train /= 255
x_test /= 255

print('Training Set: ', x_train.shape[0])
print('Test Set: ', x_test.shape[0])

#Convert the class labels to one-hot encoding
#convert class vectors to binary class matrices
y_train = keras.utils.to_categorical(y_train) #10 classes
y_test = keras.utils.to_categorical(y_test)

print(y_train[1])

#a simple multi-layer perceptron with 1 hidden layer with 128 nodes
#model = Sequential() #linear stack of layers
##dense layer is just a regular layer of neurons in a neural network
#model.add(Dense(128, activation='relu',input_shape=(784,)))
#model.add(Dropout(0.5)) # aregularization technique used to tackle overfitting, it takes in a float between 0 and 1, which is the fraction of the neurons to drop
#model.add(Dense(10, activation='softmax')) #10 classes
#model.summary()
#
##define loss function to optimize
#model.compile(loss='categorical_crossentropy',optimizer='adam',metrics=['accuracy'])
#
##define the number of epochs for training, size of training batches
#history = model.fit(x_train,y_train,batch_size=128,epochs=5,verbose=1,validation_split=0.1)
#score = model.evaluate(x_test, y_test,verbose=0)
#print('Loss: ',score[0])
#print('Accuracy: ',score[1])

#Exercise 9a
#1. Using the same dataset, build a MLP model with 2 hidden layers with 512 nodes each.
model2 = Sequential()
model2.add(Dense(512,activation='relu',input_shape=(784,)))
model2.add(Dense(512,activation='relu',input_shape=(784,)))
model2.add(Dropout(0.5))
model2.add(Dense(10,activation='softmax'))
model2.summary()

model2.compile(loss='categorical_crossentropy',optimizer='adam',metrics=['accuracy'])
history2 = model2.fit(x_train,y_train,batch_size=128,epochs=5,verbose=1,validation_split=0.1)
score = model2.evaluate(x_test,y_test,verbose=0)
print('Loss: ',score[0])
print('Accuracy: ',score[1])

#2. Change the number of training epochs to 40, what do you observe?
model3 = Sequential()
model3.add(Dense(512,activation='relu',input_shape=(784,)))
model3.add(Dense(512,activation='relu',input_shape=(784,)))
model3.add(Dropout(0.5))
model3.add(Dense(10,activation='softmax'))
model3.summary()

model3.compile(loss='categorical_crossentropy',optimizer='adam',metrics=['accuracy'])
history3 = model3.fit(x_train,y_train,batch_size=128,epochs=40,verbose=1,validation_split=0.1)
score3 = model3.evaluate(x_test,y_test,verbose=0)
print('Loss: ',score3[0])
print('Accuracy: ',score3[1])


#Exercise 9b
#classify which news category an article belongs to based on the text
(x_train1, y_train1),(x_test1,y_test1) = reuters.load_data()
#build bag-of-words representation for each news article
tokenizer = Tokenizer(num_words=10000)
x_train1 = tokenizer.sequences_to_matrix(x_train1,mode='count')
x_test1 = tokenizer.sequences_to_matrix(x_test1,mode='count')

#convert the class labels to one-hot encoding
y_train1 = keras.utils.to_categorical(y_train1,46) #46classes
y_test1 = keras.utils.to_categorical(y_test1,46)

#1. Finish the rest of the code by building an appropriate MLP model, then training and testing it
model4 = Sequential()
model4.add(Dense(512,activation='relu',input_shape=(10000,)))
model4.add(Dropout(0.5))
model4.add(Dense(46,activation='softmax'))

model4.compile(loss='categorical_crossentropy',optimizer='adam',metrics=['accuracy'])
history4=model4.fit(x_train1,y_train1,batch_size=128,verbose=1,epochs=5,validation_split=0.1)
score4 = model4.evaluate(x_test1,y_test1,verbose=0)
print('Loss: ',score4[0])
print('Accuracy: ',score4[0])

