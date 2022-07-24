# Video API

## Contents
- Instructions
- Architecture
- Cost forecast

## Instructions
The API has 3 endpoints
- `POST api/video` to upload videos
- `GET api/video` to list all videos
- `GET api/video/<video_id>` to query a single video
- `DELETE api/video/<video_id>` delete a video

### The `POST api/video` endpoint
This uploads a video, generates a thumbnail, gif and resizes and compresses the video file, stores it all to S3

In postman do the following

1. Change the method to `POST`
2. Input the following url `http://13.40.35.228/api/video`
3. click the **Body** subtab
4. select **form-data**
5. Under `Key/Value` columns set `Key = file` and under `Value` select a file from file explorer
6. Click **Send**

This should return a json similar to

```
{
    "title": "placebo).mp4",
    "id": "62dd2d178af97a7e09b68b58"
}
```

You can now copy the `id` and perform a `GET request` like

1. Create new request
2. `http://13.40.35.228/api/video/<your_video_id>`
3. Click **Send**

This will result in a `json` that might look like 

```
{
    "title": "placebo.mp4",
    "thumbnail": "https://isebarn-vid.s3.eu-west-2.amazonaws.com/62dd2d178af97a7e09b68b58/placebo.png",
    "gif": "https://isebarn-vid.s3.eu-west-2.amazonaws.com/62dd2d178af97a7e09b68b58/placebo.gif",
    "id": "62dd2d178af97a7e09b68b58"
}
```

## Important Note
The EC2 instance type I picked is a fairly inexpensive one. Which means that the video processing might take a while. The `.png` and `.gif` generation usually takes around ~5 seconds. Once `.png` generation is complete, it will be added to the `json` when using `GET`. Same for `.gif` and `video`.
I uploaded a ~5 minute video from youtube. It's original resolution was 1280x720 and filesize was 50mb. This video took ~15 minutes to be resized and compressed (the resizing is 10 minutes and compression 5 minutes)


### The `GET api/video` endpoint
This will return all uploaded videos (also those that have not been fully processed)

In postman do the following

1. Change the method to `GET`
2. Input the following url `http://13.40.35.228/api/video`
3. Click **Send**

This should return something like

```
[
    {
        "title": "placebo.mp4",
        "thumbnail": "https://isebarn-vid.s3.eu-west-2.amazonaws.com/62dd2899a3114772abdbd5e6/placebo.png",
        "gif": "https://isebarn-vid.s3.eu-west-2.amazonaws.com/62dd2899a3114772abdbd5e6/placebo.gif",
        "id": "62dd2899a3114772abdbd5e6"
    },
    {
        "title": "short.mp4",
        "thumbnail": "https://isebarn-vid.s3.eu-west-2.amazonaws.com/62dd2c978af97a7e09b68b57/short.png",
        "gif": "https://isebarn-vid.s3.eu-west-2.amazonaws.com/62dd2c978af97a7e09b68b57/short.gif",
        "video": "https://isebarn-vid.s3.eu-west-2.amazonaws.com/62dd2c978af97a7e09b68b57/short.mp4",
        "id": "62dd2c978af97a7e09b68b57"
    },
    {
        "title": "placebo.mp4",
        "thumbnail": "https://isebarn-vid.s3.eu-west-2.amazonaws.com/62dd2d178af97a7e09b68b58/placebo.png",
        "gif": "https://isebarn-vid.s3.eu-west-2.amazonaws.com/62dd2d178af97a7e09b68b58/placebo.gif",
        "id": "62dd2d178af97a7e09b68b58"
    }
]
```

### The `GET api/video/<video_id>` endpoint
Returns a single video

In postman do the following

1. Change the method to `GET`
2. Input the following url `http://13.40.35.228/api/video/62dd2c978af97a7e09b68b57`
3. Click **Send**

This will return

```
{
    "title": "short.mp4",
    "thumbnail": "https://isebarn-vid.s3.eu-west-2.amazonaws.com/62dd2c978af97a7e09b68b57/short.png",
    "gif": "https://isebarn-vid.s3.eu-west-2.amazonaws.com/62dd2c978af97a7e09b68b57/short.gif",
    "video": "https://isebarn-vid.s3.eu-west-2.amazonaws.com/62dd2c978af97a7e09b68b57/short.mp4",
    "id": "62dd2c978af97a7e09b68b57"
}
```

### The `DELETE api/video/<video_id>` endpoint
Used to delete a single video and all its resources

In postman do the following

1. Change the method to `DELETE`
2. Input the following url `http://13.40.35.228/api/video/<video_id>`
3. Click **Send**

This will return `1` to indicate success


## Architecture

### AWS
On AWS we have a simple setup. A mini EC2 ubuntu instance and an s3 instance
On the EC2 port 80 is open to the outside world. A mongodb docker container is running to store the information about the videos, and a flask server is running
The flask server has access to both the mongodb and to the s3 instance

### Flask server
The flask server consists of 3 things:

1. Endpoints
2. MongoDB interface
3. AWS S3 interface

### Uploading a new video
When a video is uploaded the following happens:

1. The file is extracted from the request
2. A new entry in mongodb is created
3. The server returns to Postman the resulting mongodb object (containing only the filename and id)
4. The server starts a thread in the background (so the user does not need to wait for the processing to complete)
5. [Thread] The id of the mongodb entry is used to create a folder of the same name
6. [Thread] The file is stored in this folder
7. [Thread] The file is loaded into a ffmpeg interface python package
8. [Thread] The ffmpeg package creates a thumbnail, uploads it to S3 and updates the mongodb object by storing the thumbnail url
9. [Thread] The ffmpeg package creates a gif, uploads it to S3 and updates the mongodb object by storing the gif url
10. [Thread] The ffmpeg package resizes the video
11. [Thread] The ffmpeg package compresses the vide
12. [Thread] The video is uploaded to S3 and the mongodb object updated by storing the video url
13. [Thread] The folder that holds the temporary objects (png, gif and video) is deleted
14. [Thread] Thread exists
15. Done

## Cost forecast

### S3
I used the AWS pricing calculator: https://calculator.aws/#/addService/S3

The assumptions are:
- 500 videos per day. That is 15000 videos per month. Each video is 7mb so that will be a total of `105GB` per month
- 50k daily users watching 20 minutes per day. That means each user will download 20 * 7 mb, 140mb, so 50k users download 210000GB per month
The total cost according to AWS is 14500USD per month

```
Internet: Tiered pricing for 215040 GB:
10240 GB x 0.09 USD per GB = 921.60 USD
40960 GB x 0.085 USD per GB = 3481.60 USD
102400 GB x 0.07 USD per GB = 7168.00 USD
61440 GB x 0.05 USD per GB = 3072.00 USD
```

### Using Cloudfront
I know what cloudfront is but I've never used it. It is an interface for API's hosted on AWS. CloudFront can reduce the costs to almost **nothing** because when serving the data through cloudfront, it gets cached (meaning not retrieved twice from s3) so popular videos incurr way less costs.

### Other costs to consider

#### Video processing
Depending on how quickly videos must be processed, better EC2's might be necessary.
The EC2's in the **Accelerated Computed** category have GPU's that might speed up video processing by a lot
They are not super expensive, there are options that are below 1USD/hour and a few ones that go to 15USD/hour.

#### Database
The database does not currently need a lot, it's just documents with 5 entries so it would be a while before it would be necessary to think about managed databases.

#### Requests
This is almost negligible, $0.60 per 1 million requests ($0.0000006 per request)












