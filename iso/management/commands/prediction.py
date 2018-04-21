import pytz
import pandas as pd
from datetime import datetime
import os
import time
import warnings
import numpy as np
from numpy import newaxis
from keras.layers.core import Dense, Activation, Dropout
from keras.layers.recurrent import LSTM
from keras.models import Sequential
import matplotlib.pyplot as plt

from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware

from iso.models import Price

pd.options.mode.use_inf_as_na = True

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings('ignore')


def load_data(data, seq_len):
    sequence_length = seq_len + 1
    result = []
    for index in range(len(data) - sequence_length):
        result.append(data[index: index + sequence_length])

    result = np.array(result)

    row = round(0.9 * result.shape[0])
    train = result[:int(row), :]
    np.random.shuffle(train)
    x_train = train[:, :-1]
    y_train = train[:, -1]
    x_test = result[int(row):, :-1]
    y_test = result[int(row):, -1]

    x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1], 1))
    x_test = np.reshape(x_test, (x_test.shape[0], x_test.shape[1], 1))

    return [x_train, y_train, x_test, y_test]


def build_model(layers):
    model = Sequential()

    model.add(LSTM(
        input_shape=(layers[1], layers[0]),
        output_dim=layers[1],
        return_sequences=True))
    model.add(Dropout(0.2))

    model.add(LSTM(
        layers[2],
        return_sequences=False))
    model.add(Dropout(0.2))

    model.add(Dense(
        output_dim=layers[3]))
    model.add(Activation('linear'))

    start = time.time()
    model.compile(loss='mse', optimizer='rmsprop')
    print('Compilation Time: ', time.time() - start)
    return model


def predict_point_by_point(model, data):
    # Predict each timestep given the last sequence of true data, in effect only predicting 1 step ahead each time
    predicted = model.predict(data)
    predicted = np.reshape(predicted, (predicted.size,))
    return predicted


def predict_sequence_full(model, data, window_size):
    # Shift the window by 1 new prediction each time, re-run predictions on new window
    curr_frame = data[0]
    predicted = []
    for i in range(len(data)):
        predicted.append(model.predict(curr_frame[newaxis, :, :])[0, 0])
        curr_frame = curr_frame[1:]
        curr_frame = np.insert(curr_frame, [window_size - 1], predicted[-1], axis=0)
    return predicted


def predict_sequences_multiple(model, data, window_size, prediction_len):
    # Predict sequence of 50 steps before shifting prediction run forward by 50 steps
    prediction_seqs = []
    for i in range(int(len(data) / prediction_len)):
        curr_frame = data[i * prediction_len]
        predicted = []
        for j in range(prediction_len):
            predicted.append(model.predict(curr_frame[newaxis, :, :])[0, 0])
            curr_frame = curr_frame[1:]
            curr_frame = np.insert(curr_frame, [window_size - 1], predicted[-1], axis=0)
        prediction_seqs.append(predicted)
    return prediction_seqs


def plot_results(predicted_data, true_data):
    fig = plt.figure(facecolor='white')
    ax = fig.add_subplot(111)
    ax.plot(true_data, label='True Data')
    plt.plot(predicted_data, label='Prediction')
    plt.legend()
    plt.show()


def plot_results_multiple(predicted_data, true_data, prediction_len):
    fig = plt.figure(facecolor='white')
    ax = fig.add_subplot(111)
    ax.plot(true_data[-100:], label='True Data')
    # Pad the list of predictions to shift it in the graph to it's correct start
    for i, data in enumerate(predicted_data):
        padding = [None for p in range(i * prediction_len)]
        plt.plot(padding + data[-100:], label='Prediction')
        plt.legend()
    plt.show()


class Command(BaseCommand):
    def handle(self, *args, **options):
        print('Loading data... ')
        global_start_time = time.time()
        epochs = 1
        seq_len = 50

        nodes = ['MENLO_6_N004', 'GLENWOOD_6_N005', 'WOODSIDE_6_N004', 'BLLEHVN_6_N009', 'SARATOGA_2_N011']
        start = make_aware(datetime(2016, 1, 1), pytz.timezone('America/Los_Angeles'))
        end = make_aware(datetime(2018, 1, 1), pytz.timezone('America/Los_Angeles'))
        price_records = Price.objects.filter(start__gte=start, start__lt=end) \
            .order_by('start') \
            .values('start', 'node', 'price')
        price_df = pd.DataFrame.from_records(price_records)
        price_df['start'] = price_df['start'].dt.tz_convert('US/Pacific').dt.tz_localize(None)

        # price_df['day_of_week'] = price_df['start'].dt.weekday
        # price_df['week_of_year'] = price_df['start'].dt.week
        # price_df['time_of_day'] = price_df['start'].dt.time
        # price_df['day_of_year'] = price_df['start'].dt.dayofyear

        upper = price_df['price'].quantile(0.99)
        lower = price_df['price'].quantile(0.01)

        price_df.loc[price_df['price'] > upper, 'price'] = upper
        price_df.loc[price_df['price'] < lower, 'price'] = lower
        price_df.loc[price_df['price'] == 0, 'price'] = 0.01
        price_df['price_normalized'] = price_df.groupby(['node'])['price'].transform(
            lambda x: (x - list(x)[0]) / list(x)[0])

        series = price_df[price_df['node'] == nodes[0]]['price_normalized']
        X_train, y_train, X_test, y_test = load_data(list(series), seq_len)

        print('Data Loaded. Compiling...')

        model = build_model([1, 50, 100, 1])

        model.fit(
            X_train,
            y_train,
            batch_size=512,
            nb_epoch=epochs,
            validation_split=0.05)

        # predictions = predict_sequences_multiple(model, X_test, seq_len, 50)
        # predicted = predict_sequence_full(model, X_test, seq_len)
        predicted = predict_point_by_point(model, X_test)

        print('Training duration (s) : ', time.time() - global_start_time)
        plot_results(predicted[0:200], y_test[0:200])
        # plot_results_multiple(predictions, y_test, 50)

        # price_df['time_of_day'] = pd.Categorical(price_df['time_of_day']).codes
        # price_df['day_of_week'] = pd.Categorical(price_df['day_of_week']).codes
        # price_df['week_of_year'] = pd.Categorical(price_df['week_of_year']).codes
        # price_df['day_of_year'] = pd.Categorical(price_df['day_of_year']).codes

        # X = price_df[['time_of_day', 'day_of_week', 'week_of_year', 'day_of_year']]
        # y = price_df['change']
        # X = sm.add_constant(X)

        # print(X.describe())

        # model = sm.OLS(y.astype(float), X, missing='drop').fit()
        # price_df['prediction'] = model.predict(X)
        #
        # print(price_df[['start', 'node', 'change', 'prediction']].head(20))
