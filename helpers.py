import matplotlib.image as mpimg
import numpy as np
import matplotlib.pyplot as plt
import os,sys
from PIL import Image
import sys
sys.path.append('/usr/lib/python3.5/site-packages')
import cv2
from skimage import (color,feature,filters,draw,morphology,segmentation)
from skimage.future import graph
from sklearn.metrics import pairwise_distances_argmin
from sklearn.utils import shuffle
from sklearn.cluster import KMeans
from scipy import ndimage
from skimage.transform import (hough_line, hough_line_peaks,
                               probabilistic_hough_line,rescale)
from scipy import cluster

def get_features_edges(imgs,grid_step,canny_sigma):

    w = imgs[0].shape[1]
    h = imgs[0].shape[0]
    X_edge = np.asarray([ feature.canny(color.rgb2gray(imgs[i]),sigma=canny_sigma) for i in range(len(imgs))])
    patches = [img_crop(X_edge[i], grid_step, grid_step) for i in range(len(X_edge))]
    patches = np.asarray([np.mean(patches[i][j]).astype(int) for i in range(len(patches)) for j in range(len(patches[i]))])

    return patches.reshape(-1,1)

def get_features_vq_colors(imgs,grid_step,codebook):

    w = imgs[0].shape[1]
    h = imgs[0].shape[0]
    X_rgb = [ recreate_image(codebook,cluster.vq.vq(imgs[i].reshape(w*h,-1), codebook)[0],w,h) for i in range(len(imgs))]
    patches = [img_crop(X_rgb[i], grid_step, grid_step) for i in range(len(X_rgb))]
    patches = np.asarray([np.mean(patches[i][j]).astype(int) for i in range(len(patches)) for j in range(len(patches[i]))])

    return patches.reshape(-1,1)

def get_features_hist(imgs,n_bins,grid_step):
    patches = [img_crop(imgs[i], grid_step, grid_step) for i in range(len(imgs))]
    patches = np.asarray([np.asarray((np.histogram(patches[i][j][:,:,0],n_bins)[0],
                            np.histogram(patches[i][j][:,:,1],n_bins)[0],
                            np.histogram(patches[i][j][:,:,2],n_bins)[0])).reshape(1,-1)
                           for i in range(len(patches)) for j in range(len(patches[i]))])

    return patches.reshape(-1,3*n_bins)

def get_features_dt(imgs,canny_sigma,grid_step):
    X_dt = np.asarray([ distance_transform_edge(color.rgb2gray(imgs[i]),edge_sigma=canny_sigma) for i in range(len(imgs))])
    patches = [img_crop(X_dt[i], grid_step, grid_step) for i in range(len(X_dt))]
    patches = np.asarray([np.mean(patches[i][j]).astype(int) for i in range(len(patches)) for j in range(len(patches[i]))])

    return patches.reshape(-1,1)

    X_dt = X_dt[:,::grid_step,::grid_step].reshape(-1,1)
    X_dt = (X_dt - np.mean(X_dt))/np.var(X_dt)
    return X_dt

def distance_transform_edge(img,edge_sigma=1):

    edge_map = feature.canny(img,sigma=edge_sigma)
    dt = ndimage.distance_transform_cdt(~edge_map,metric='taxicab')

    return dt

def distance_transform(mat,edge_sigma=1):

    dt = ndimage.distance_transform_cdt(mat,metric='taxicab')

    return dt

def my_thr(img,rel_thr,sigma):

    img_thr = np.zeros((img.shape[0],img.shape[1]))
    if sigma is not None:
        img = filters.gaussian(img,sigma,multichannel=True)
    img_thr = color.rgb2gray(img)
    img_thr = (img_thr-np.mean(img_thr))/np.std(img_thr)
    high_thr = np.mean(img_thr)+rel_thr*np.std(img_thr)
    low_thr = np.mean(img_thr)-rel_thr*np.std(img_thr)
    img_thr[np.where(img_thr > high_thr)] = 0
    img_thr[np.where(img_thr < low_thr)] = 0

    return img_thr

def get_features_hough(imgs,rel_thr,max_n_lines, grid_step=1,sig_canny=1,radius=1,threshold=10, line_length=45,line_gap=3):

    hough_maps = [ make_hough(imgs[i],rel_thr, max_n_lines,sig_canny,radius,threshold,line_length,line_gap) for i in range(len(imgs))]
    patches_per_image = [img_crop(hough_maps[i], grid_step, grid_step) for i in range(len(hough_maps))]
    import pdb; pdb.set_trace()
    patches = np.asarray([np.mean(patches_per_image[i][j].astype(int)) for i in range(len(patches_per_image)) for j in range(len(patches_per_image[i]))])

    return patches.reshape(-1,1)

def make_hough(img,rel_thr,max_n_lines,sig_canny=1,radius=1,threshold=10, line_length=45,line_gap=3,slic_segments = 400, gc_thresh=0.05):

    #Hough-lines extractor
    elem = morphology.disk(1)
    hough_lines = list()
    im = np.abs(my_thr(img,rel_thr,sig_canny))
    edges = filters.sobel(color.rgb2gray(img))
    labels1 = segmentation.slic(img, compactness=30, n_segments=slic_segments)
    g = graph.rag_boundary(labels1,edges)
    labels2 = graph.cut_threshold(labels1, g,thresh=gc_thresh)
    gc_img = color.label2rgb(labels2, img, kind='avg')

    hough_map = np.zeros((im.shape[0],im.shape[1],3))

    lines = probabilistic_hough_line(im, threshold=threshold, line_length=line_length,line_gap=line_gap)
    line_idx = list()
    line_std_rgb = list()

    for line in lines:
        p0, p1 = line
        line_idx.append( draw.line(p0[1], p0[0], p1[1], p1[0]))
        line_std_rgb.append(np.min(np.std(gc_img[line_idx[-1][0],line_idx[-1][1]],axis=0)))
        #hough_lines[-1][line_idx] = 1
    line_std_rgb = np.asarray(line_std_rgb)
    line_std_idx = np.argsort(line_std_rgb)
    for i in range(np.min((max_n_lines,len(lines)))):
        this_line_idx = line_idx[line_std_idx[i]]
        this_line_labels = np.unique(labels2[this_line_idx[0],this_line_idx[1]])
        for i in np.unique(this_line_labels):
            this_label_idx = np.where(labels2 == i)
            hough_map += gc_img[this_label_idx[0],this_label_idx[1],:]

    return hough_map

def recreate_image(codebook, labels, w, h):
    """Recreate the (compressed) image from the code book & labels"""
    d = codebook.shape[1]
    image = np.zeros((w, h, d))
    label_idx = 0
    for i in range(w):
        for j in range(h):
            image[i][j] = codebook[labels[label_idx]]
            label_idx += 1
    return image

def kmeans_img(img,n_clusters):
    # Load Image and transform to a 2D numpy array.
    w, h, d = original_shape = tuple(img.shape)
    assert d == 3
    image_array = np.reshape(img, (w * h, d))

    #print("Fitting model on a small sub-sample of the data")
    image_array_sample = shuffle(image_array, random_state=0)[:1000]
    kmeans = KMeans(n_clusters=n_clusters, random_state=0).fit(image_array_sample)

    # Get labels for all points
    #print("Predicting color indices on the full image (k-means)")
    labels = kmeans.predict(image_array)
    #print("done in %0.3fs." % (time() - t0))

    codebook_random = shuffle(image_array, random_state=0)[:n_clusters + 1]
    #print("Predicting color indices on the full image (random)")
    labels_random = pairwise_distances_argmin(codebook_random,image_array, axis=0)

    return recreate_image(kmeans.cluster_centers_, labels, w, h)

def get_features_sift(imgs,canny_sigma,sift_sigmas,grid_step,return_kps=False):

    X_sift = np.asarray([ get_sift_densely(imgs[i],step=grid_step,sigmas=sift_sigmas,mode='neighborhood',return_kps=False) for i in range(len(imgs))])
    X_sift = X_sift.reshape(len(imgs)*X_sift.shape[1],-1)

    return X_sift

def get_sift_densely(img,step=1,sigmas=None,mode='neighborhood',subsampl_step = 2,macro_length=2,return_kps=False):

    def do_it(img,step):
        sift = cv2.xfeatures2d.SIFT_create(sigma=1)
        kpDense = [cv2.KeyPoint(x, y, step) for y in range(0, img.shape[0], step)  for x in range(0, img.shape[1], step)]
        img = (color.rgb2gray(img)*255).astype(np.uint8)
        kps,des = sift.compute(color.rgb2gray(img),kpDense)
        des = des/np.linalg.norm(des,axis=1).reshape(-1,1)
        des[np.where(des >= 0.2)] = 0.2
        des = des/np.linalg.norm(des,axis=1).reshape(-1,1)

        return des

    if((sigmas is None) and mode is not 'neighborhood'): return do_it(img,step)
    if((sigmas is None) and mode is 'neighborhood'):
        des = list()
        this_des = do_it(img,1).reshape(img.shape[0],img.shape[1],-1)
        centers = [(x,y) for y in np.arange(0, img.shape[0], step)  for x in np.arange(0, img.shape[1], step)]
        for i in range(len(centers)):
            idx_i = np.arange(centers[i][0]-macro_length*subsampl_step/2, centers[i][0] + macro_length*subsampl_step/2 + 1 , subsampl_step).astype(int)
            idx_j = np.arange(centers[i][1]-macro_length*subsampl_step/2, centers[i][1] + macro_length*subsampl_step/2 + 1 , subsampl_step).astype(int)
            des.append(this_des.take(idx_i,mode='wrap',axis=0).take(idx_j,mode='wrap',axis=1).ravel())

        res = np.asarray(des)
        if(return_kps):
            return(res,centers)
        else:
            return res

    else:
        des = list()
        for i in range(len(sigmas)):
            des.append(do_it(filters.gaussian(img,sigmas[i],multichannel=True),step))

        res = np.asarray(des)
        res = np.transpose(res,(1,2,0))

        return res.reshape(res.shape[0],res.shape[1]*res.shape[2])

def load_image(infilename):
    data = mpimg.imread(infilename)
    return data

def rgb_remove_green(img):
    img[:,:,1] = np.zeros((img.shape[0],img.shape[1]))
    return img

def img_float_to_uint8(img):
    rimg = img - np.min(img)
    rimg = (rimg / np.max(rimg) * 255).round().astype(np.uint8)
    return rimg

# Concatenate an image and its groundtruth
def concatenate_images(img, gt_img):
    nChannels = len(gt_img.shape)
    w = gt_img.shape[0]
    h = gt_img.shape[1]
    if nChannels == 3:
        cimg = np.concatenate((img, gt_img), axis=1)
    else:
        gt_img_3c = np.zeros((w, h, 3), dtype=np.uint8)
        gt_img8 = img_float_to_uint8(gt_img)
        gt_img_3c[:,:,0] = gt_img8
        gt_img_3c[:,:,1] = gt_img8
        gt_img_3c[:,:,2] = gt_img8
        img8 = img_float_to_uint8(img)
        cimg = np.concatenate((img8, gt_img_3c), axis=1)
    return cimg

def img_crop_sp(im, n_segments, compactness):
    list_patches = []
    imgwidth = im.shape[0]
    imgheight = im.shape[1]
    is_2d = len(im.shape) < 3
    segments = slic(im,n_segments=n_segments,compactness=compactness)

def img_crop(im, w, h):
    list_patches = []
    imgwidth = im.shape[0]
    imgheight = im.shape[1]
    is_2d = len(im.shape) < 3
    for i in range(0,imgheight,h):
        for j in range(0,imgwidth,w):
            if is_2d:
                im_patch = im[j:j+w, i:i+h]
            else:
                im_patch = im[j:j+w, i:i+h, :]
            list_patches.append(im_patch)
    return list_patches

# Extract 6-dimensional features consisting of average RGB color as well as variance
def extract_features(img):
    feat_m = np.mean(img, axis=(0,1))
    feat_v = np.var(img, axis=(0,1))
    feat = np.append(feat_m, feat_v)
    return feat

# Extract 2-dimensional features consisting of average gray color as well as variance
def extract_more_features_2d(img):
    feat_m = np.mean(img)
    feat_v = np.var(img)
    feat = np.append(feat_m, feat_v)
    return feat

# Extract 2-dimensional features consisting of average gray color as well as variance
def extract_features_2d(img):
    feat_m = np.mean(img)
    feat_v = np.var(img)
    feat = np.append(feat_m, feat_v)
    return feat

# Extract features for a given image
def extract_img_features(filename,patch_size):
    img = load_image(filename)
    img_patches = img_crop(img, patch_size, patch_size)
    X = np.asarray([ extract_features_2d(img_patches[i]) for i in range(len(img_patches))])
    return X

def value_to_class(v,thr):
    df = np.sum(v)
    if df > thr:
        return 1
    else:
        return 0


def label_to_img(imgwidth, imgheight, w, h, labels):
    im = np.zeros([imgwidth, imgheight])
    idx = 0
    for i in range(0,imgheight,h):
        for j in range(0,imgwidth,w):
            im[j:j+w, i:i+h] = labels[idx]
            idx = idx + 1
    return im

def make_img_overlay(img, predicted_img):
    w = img.shape[0]
    h = img.shape[1]
    color_mask = np.zeros((w, h, 3), dtype=np.uint8)
    color_mask[:,:,0] = predicted_img*255

    img8 = img_float_to_uint8(img)
    background = Image.fromarray(img8, 'RGB').convert("RGBA")
    overlay = Image.fromarray(color_mask, 'RGB').convert("RGBA")
    new_img = Image.blend(background, overlay, 0.2)
    return new_img

def PIL2array(img):
    return np.array(img.getdata(),
                    np.uint8).reshape(img.size[1], img.size[0], 4)
