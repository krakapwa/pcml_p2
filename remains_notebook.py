
# Plot features using predictions to color datapoints
plt.scatter(X[:, 0], X[:, 1], c=Z, edgecolors='k', cmap=plt.cm.Paired); plt.show()

# Run prediction on the img_idx-th image
img_idx = 12

Xi = hp.extract_img_features(image_dir + files[img_idx],patch_size)
Zi = logreg.predict(Xi)
plt.scatter(Xi[:, 0], Xi[:, 1], c=Zi, edgecolors='k', cmap=plt.cm.Paired)

# Display prediction as an image
w = gt_imgs[img_idx].shape[0]
h = gt_imgs[img_idx].shape[1]
predicted_im = hp.label_to_img(w, h, patch_size, patch_size, Zi)
cimg = hp.concatenate_images(imgs[img_idx], predicted_im)
fig1 = plt.figure(figsize=(10, 10)) # create a figure with the default size 
plt.imshow(cimg, cmap='Greys_r');
plt.title('Prediction')
plt.show()

new_img = hp.make_img_overlay(imgs[img_idx], predicted_im)

plt.imshow(new_img);
plt.title('Prediction')
plt.show()

#Make submission
masks_to_submission('submission_test.csv', *image_filenames)

#Hough-lines extractor 
hough_lines = list()
for i in range(n):
    im = color.rgb2gray(imgs[i])
    hough_lines.append(np.zeros((im.shape[0],im.shape[1])))
    edge = feature.canny(im)
    lines = probabilistic_hough_line(edge, threshold=10, line_length=45,line_gap=3)
    for line in lines:
        p0, p1 = line
        line_idx = skimage.draw.line(p0[1], p0[0], p1[1], p1[0])
        hough_lines[-1][line_idx] = 1

#histogram feature computation
X_hist0 = np.asarray([ np.histogram(img_patches[i][:,:,0],bins=hist_bins,density=True)[0] for i in range(len(img_patches))])
X_hist1 = np.asarray([ np.histogram(img_patches[i][:,:,1],bins=hist_bins,density=True)[0] for i in range(len(img_patches))])
X_hist2 = np.asarray([ np.histogram(img_patches[i][:,:,2],bins=hist_bins,density=True)[0] for i in range(len(img_patches))])
