# CS_IOC5008_HW4
Code for instance segmentation

reference: [You Only Look At CoefficienTs](https://github.com/dbolya/yolact)

## Hardware
The following specs were used to create the original solution.
- Ubuntu 18.04 LTS
- 1x NVIDIA 1080 


## Code Structure
```
 +- data
 |  +- config.py: the setting of backbone of model and the path of dataset
 |  +- dataloader.py: using to download training and testing data
 +- models
 | +- backbone.py: the backbone(resnet101+FPN) of this model
 | +- box_utils.py: using to calculate IOU of bbox or mask
 | +- detection.py: using to calculate NMS
 | +- interpolate.py: class to interpolate
 | +- model.py: the whole predict model
 | +- multibox_loss.py: using to calculate the bbox loss, label loss, mask loss, and segmentation loss
 | +- output_utils.py: post processing for the output of model
 +- utils
 |  +- augmentation.py: function for data augmentation
 |  +- functions.py: using to print processing bar
 |  +- timer.py: using to print training time
 +- train.py: using to train the model
 +- predict.py: using to predict the mask of input images
 +- make_submission.py: using to output .json file for submit
 +- config.yaml: setting for training, predict, and make submission
```

## Usage

### Dataset Preparation
All required files except images are already in data directory. <br>
You need to [download](https://drive.google.com/drive/folders/1fGg03EdBAxjFumGHHNhMrz2sMLLH04FK) the training data and testing data by youself.<br>
After downloading images, the data directory is structured as:
```
dataset
  +- train_images
  |  +- 2007_000033.jpg
  |  +- 2007_000042.jpg
  |  +- 2007_000061.jpg
  |  +- ...
  +- pascal_train.json
  +- test_images
  |  +- 2007_000629.jpg
  |  +- 2007_001157.jpg
  |  +- 2007_001239.jpg
  |  +- ...
  +- test.json
```

### Training
You can change training setting in data/config.py and config.yaml and run the following command to train.
```
$ python3 train.py --config=config.yaml
```


### Predict
You can change the path of input and output images in config.yaml and run the following command to predict the result of segmentation.
```
$ python3 predict.py --config=config.yaml
```

### Make Submission
You can change the path of testing .json file in config.yml and run the following command to predict the result of segmentation. <br>
If you want to calculate mAP, change the option calc_mAP to True in config.yaml.
```
$ python3 make_submission.py --config=config.yaml
```

