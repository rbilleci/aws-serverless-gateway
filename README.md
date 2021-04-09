# AWS Serverless Gateway for S3

This project demonstrates a custom serverless gateway to Amazon S3. 

The motivation for this project originated from the requirement to serve
files from S3, supporting  custom authorization mechanisms, filtering 
results, caching, rate-limiting of requests, and download payload sizes of 20 GB. 

The solution uses Amazon CloudFront as the entry-point for requests, 
with AWS Lambda@Edge for custom authorizations and filtering, 
and the AWS Web Application Firewall for security and rate-limiting. 

Amazon CloudFront with Lamda@Edge were ideal as they allow for custom logic to be 
incorporated at the points in a request:

* After CloudFront receives a request from a viewer (viewer request)
* Before CloudFront forwards the request to the origin (origin request)
* After CloudFront receives the response from the origin (origin response)
* Before CloudFront forwards the response to the viewer (viewer response)

Before selecting Amazon CloudFront as the core of the solution architecture, 
the following alternatives were analyzed:
* **AWS API Gateway + S3** - this alternative is not acceptable due to a response size 
   limit of 10 MB, enforced by the AWS API Gateway.
* **AWS Application Load Balancer + AWS Lambda + S3** - this alternative downloads S3 
   objects through an AWS Lambda function. This alternative is not acceptable due to 
   1.) higher costs for keeping AWS Lambda functions running during S3 downloads, 
   2.) a response size limit of 6 MB, enforced by AWS Lambda, and 
   3.) limited options to inject custom logic.  


This project uses S3 as its origin, but it can be adapted to other use cases, 
such as building a serverless API gateway in-front of AWS Lambda functions.


### Architecture

* **Amazon CloudFront Distribution** - the "gateway" or entry point for all requests. 
* **AWS Web Application Firewall (WAF)** - integrated with the Amazon CloudFront Distribution, 
  offers security features to allow/block requests based on requests.
* **S3** - stores objects served by the gateway. 

### Installation

You can install the solution as-is, and it will proxy GET all requests to S3.
If you want to add custom authorization logic, you'll need to complete 
the boiler-plate code in the **authorize** function of **src/serverless-gateway.py**.

#### Prerequisites

1. If you have an existing S3 bucket you will use, note down the bucket name. 
   Or, create a new S3 bucket and populate it with some files.
   Note, that if you have an S3 bucket that already has a policy assigned to it, 
   this CloudFormation template in this package will need to be modified. The current version expects that no 
   bucket policy exists on the bucket.
2. If you want to use a custom domain, 
   create/import a certificate into the AWS Certificate Manager in the `us-east-1` region. You'll need to
   note down the ARN of the certificate as well
   as the domain name you'll use.
3. Make sure the AWS SAM CLI is installed. See: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html   
4. Make sure you run `aws configure` and configure the account info. Since we are using Amazon CloudFront, make sure to set the region to `us-east-1`

#### Deploy

1. Check out the project from GitHub to a local machine
2. Open the file `src/serverless-gateway.py` and changed the bucket name constant 
   to the value of your S3 bucket:

        S3_BUCKET_NAME = "serverless-gateway"
3. Open a terminal and go to the directory where you've checked out the project. 
   From the terminal, run the following commands:
   
        sam build
        sam deploy --guided

    You'll be guided through an interactive deployment process and ask to
    enter values for the deployment parameters.
    The first time you run the deployment, try using the default value for
    each parameter.
    The only parameter you **must** provide is the S3 parameter, as it empty.
    This must be the `S3 bucket name` where the
    gateway will serve files from.
4. The first deployment may take up to 30 minutes. When the deployment is complete
   there will be a CloudFormation output with the CloudFront domain name. 
   You can use this domain name to access the bucket through the serverless gateway,
   or, of you installed a custom domain, you can also use that.


### Estimated Pricing

Pricing is < 3.50 USD / month per 1 million requests. The price breakdown follows:

* 1.00 USD - Amazon CloudFront 
* 0.79 USD - Lambda@Edge
* 0.50 USD - Lambda@Edge CloudWatch logs
* 0.40 USD - S3 get requests
* 0.60 USD - AWS WAF 

Assumptions for the pricing include:
* Pricing is based on US-EAST-1, as of April 9, 2021. 
* Data transfer costs are not considered
* Free tier is not used, which may bring most customer costs down considerably
* Caching is not considered, which may reduce costs  
* there is a fixed costs for AWS WAF rules of approximately 5-10 USD / month
