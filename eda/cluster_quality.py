# -*- coding: utf-8 -*-

import sys
import os
import h5py
import csv
import numpy as np
from PIL import Image

import matplotlib as mpl
mpl.use('TkAgg')
import matplotlib.pyplot as plt

# ugly way to import a file from another directory ...
sys.path.append(os.path.join(os.path.dirname(__file__), '../model'))
import model
from config_emoji import dset, img_rows, img_cols, img_chns, img_mode

base = '/Users/yliu0/data/emoji/'
dims = [4, 8, 16, 32, 64, 128, 256, 512, 1024]
models = {} # re-use keras models

def create_model (latent_dim):
    ba = '{}emoji_result/{}/'.format(base, latent_dim)
    mpath = ba + '{}_model_dim={}.json'.format(dset, latent_dim)
    wpath = ba + '{}_model_dim={}.h5'.format(dset, latent_dim)
    m = model.Vae(latent_dim = latent_dim, img_dim=(img_chns, img_rows, img_cols))
    models[latent_dim] = m.read(mpath, wpath) + (m,)

# read latent space
def read_ls (latent_dim):
    rawpath = '{}/latent/latent{}.h5'.format(base, latent_dim)
    with h5py.File(rawpath, 'r') as f:
        X = np.asarray(f['latent'])
    return X

def read_meta ():
    res = []
    with open(base + 'database.csv', 'rb') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for row in reader:
            if row[0] == 'index':
                continue # skip header
            # i, category, name, platform, version, codepoints, shortcode
            res.append(row[0:5] + row[7:9])
    return res

def group_by (meta, col):
    res = {}

    for row in meta:
        c = row[col]
        i = int(row[0])
        if c in res:
            res[c].append(i)
        else:
            res[c] = [i]
    
    return res

# deprecated
# turns out creating a giant matrix is a bad idea ...
def pointwise_dist_dep (X):
    n, latent_dim = X.shape

    # prepare matrices
    L = np.empty([0, latent_dim])
    R = np.empty([0, latent_dim])
    for i in range(n):
        # left hand matrix: repeat an element N times
        L = np.concatenate((L, np.repeat([X[i]], n, axis=0)), axis=0)

        # right hand matrix: every element
        R = np.concatenate((R, X), axis=0)
    
    # compute distance
    D = np.linalg.norm(L-R, axis=1)

    # take average
    d = np.sum(D) / float(n * (n-1))
    return d

# compute the average inter-point distance (L2) between each point pair
def pointwise_dist (X, Y=None):
    R = X if Y is None else Y
    m, _ = X.shape
    n, _ = R.shape

    s = 0
    for i in range(m):
        # left hand matrix: repeat an element N times
        L = np.repeat([X[i]], n, axis=0)
        D = np.linalg.norm(L - R, axis=1)
        # for intra-cluster distance, exclude self
        denom = n - 1 if Y is None else n
        s += np.sum(D) / float(denom)
    
    return s / float(m)

def pointwise_hist (X):
    n, latent_dim = X.shape

    bins = np.arange(0, 20, 0.5)
    hist = np.zeros(bins.shape[0] - 1, dtype=int)
    for i in range(n):
        # left hand matrix: repeat an element N times
        L = np.repeat([X[i]], n, axis=0)
        D = np.linalg.norm(L - X, axis=1)
        h, _ = np.histogram(D, bins = bins)
        h[0] -= 1 # exclude self edge
        hist += h
    
    return hist, bins

# print the global average pointwise distance for each latent dim
def report_baseline ():
    for dim in dims:
        X = read_ls(dim)
        # running over all points will take too long, so we just go for a sample
        # -- how accurate is this approximation?
        # -- 8.377 (all points) vs 8.530 (first 1000) in dim=32
        dist = pointwise_dist(X[0:1000])
        print 'Latent Dimension: {}'.format(dim)
        print 'Average point-wise distance: {}'.format(dist)

# produce a csv of intra-cluster distances of clusters defined in groups
def report_cluster (X, groups, out):
    res = []
    for k in groups.keys():
        if k == '':
            continue # skip empty key
        a = pointwise_dist(X[groups[k]])
        b = pointwise_dist(X[groups[k]], np.delete(X, groups[k], axis=0))
        score = (b - a) / max(a, b)
        res.append([k, int(score * 100)])

    # sort by intra-cluster distance
    res.sort(key = lambda x : x[1], reverse = True)

    with open('./{}'.format(out), 'wb') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')
        for row in res:
            writer.writerow(row)

# cluster quality by shortcode
def report_shortcode ():
    meta = read_meta()
    codes = group_by(meta, 6) # 6 is the column for shortcode
    dim = 4
    X = read_ls(dim)
    report_cluster(X, codes, './result/shortcode_{}.csv'.format(dim))

# draw a histogram
def draw_hist (hist, bins, fn):
    fig, ax = plt.subplots()
    bar_width = 0.3

    rect = ax.bar(bins[1:], hist, bar_width)
    ax.set_xlabel('Point-wise Distance')
    ax.set_ylabel('Count')
    fig.savefig('./result/dist_{}.png'.format(fn))

# draw a histogram for point-wise ditance for each latent dim
def report_distance_hist ():
    for dim in dims:
        X = read_ls(dim)
        hist, bins = pointwise_hist(X[0:1000])
        draw_hist(hist, bins, dim)

# plot summary stats per axis
def report_axis ():
    for dim in dims:
        X = read_ls(dim)
        q25 = np.percentile(X, 25, axis=0)
        q75 = np.percentile(X, 75, axis=0)
        q0 = X.min(axis=0)
        q100 = X.max(axis=0)

        plt.figure(figsize=(10, dim * 0.1 + 3))

        for i in range(dim):
            plt.plot([q25[i], q75[i]], [i, i], 'C0', linewidth=3)
            plt.plot([q0[i], q100[i]], [i, i], 'C0', linestyle='dashed')

        plt.title('Thick Line: 25th to 75th percentile. Dashed Line: min to max.')
        plt.xlabel('Percentile Value')
        plt.ylabel('Latent Space Axis')
        plt.savefig('./result/axis_{}.png'.format(dim))

# print # of axis that has some range of values
def report_valid_axis ():
    print 'The number of valid axes:'
    for dim in dims:
        X = read_ls(dim)
        q25 = np.percentile(X, 25, axis=0)
        q75 = np.percentile(X, 75, axis=0)
        d = q75 - q25
        num = (d > 0.4).sum()

        print '{} of {}'.format(num, dim)

# probe along each axis, and generate representative images
def interpolate_axis ():
    exclude = True # whether to skip unused axis
    dim = 1024
    X = read_ls(dim)
    create_model(dim)
    vae, encoder, decoder, md = models[dim]
    print 'Model created.'
    num_stops = 5

    q50 = np.percentile(X, 50, axis=0)
    res = np.zeros((img_rows * dim, img_cols * num_stops, img_chns), 'uint8')
    ii = 0
    for i in range(dim):
        col = X[:, i]
        # compute key stats
        stops = [col.min(), np.percentile(col, 25), q50[i], np.percentile(col, 75), col.max()]
        # optionally skip unused axis
        if exclude and stops[3] - stops[1] < 0.4:
            continue
        for j in range(num_stops):
            val = np.copy(q50)
            val[i] = stops[j]
            val = val.reshape((1, dim))
            recon = md.to_image(decoder.predict(val))
            img = Image.fromarray(recon, img_mode)
            res[ii*img_rows:(ii+1)*img_rows, j*img_cols:(j+1)*img_cols, :] = recon
        ii += 1 # because we skip some axis

    img = Image.fromarray(res[:img_rows*ii, :, :], img_mode)
    img.save('./result/representative_{}.png'.format(dim))

if __name__ == '__main__':
    report_shortcode()
