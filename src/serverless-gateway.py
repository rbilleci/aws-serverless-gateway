import json
import boto3
from http import HTTPStatus
from urllib.parse import parse_qs
from constants import S3_DELIMITER, MAX_KEYS, PARAMETER_MAX_KEYS, PARAMETER_START_AFTER, MIN_KEYS_FETCH_SIZE

S3_BUCKET_NAME = "serverless-gateway"  # change or implement resolve_s3_bucket_name()
S3_CLIENT = boto3.client('s3')


def handler(event, context):
    authorize(event, context)
    request = event['Records'][0]['cf']['request']
    method = request['method']
    if method == "GET":
        return handle_get(request)
    else:
        return {"status": HTTPStatus.METHOD_NOT_ALLOWED.real}


def authorize(event, context):
    """
    Implement your authorization function here. You have complete access to the request, and can return
    data to use for filtering list requests.
    For example, you could return a list of S3 prefixes the requester is allowed to access.
    """
    pass


def handle_get(request):
    if request['uri'].endswith(S3_DELIMITER) or len(request['uri']) == 0:
        return s3_list(request)
    else:
        return request


def s3_list(request):
    keys, start_after = s3_list_filter(request)
    return {"status": "200",
            "statusDescription": "OK",
            "headers": {"cache-control": [{"key": "Cache-Control", "value": "max-age=60"}],
                        "content-type": [{"key": "Content-Type", "value": "application/json"}]},
            "body": json.dumps({"keys": keys, "start_after": start_after})}


def s3_list_filter(request):
    parameters = {k: v[0] for k, v in parse_qs(request["querystring"]).items()}
    max_keys_to_return = resolve_max_keys_to_return(parameters)
    prefix = resolve_prefix(request)
    start_after = resolve_start_after(parameters)
    new_start_after = None
    continuation_token = None
    continuation_available = True
    keys = []

    # Query and filter keys until the max results is retrieved.
    # Due to filtering, multiple calls to S3 must be made
    while continuation_available and len(keys) < max_keys_to_return:
        if start_after is not None:
            s3_response = S3_CLIENT.list_objects_v2(Bucket=resolve_s3_bucket_name(request),
                                                    Delimiter=S3_DELIMITER,
                                                    EncodingType="url",
                                                    MaxKeys=resolve_key_fetch_size(parameters),
                                                    Prefix=prefix,
                                                    StartAfter=start_after)
        elif continuation_token is None:
            s3_response = S3_CLIENT.list_objects_v2(Bucket=resolve_s3_bucket_name(request),
                                                    Delimiter=S3_DELIMITER,
                                                    EncodingType="url",
                                                    MaxKeys=resolve_key_fetch_size(parameters),
                                                    Prefix=prefix)
        else:
            s3_response = S3_CLIENT.list_objects_v2(Bucket=resolve_s3_bucket_name(request),
                                                    Delimiter=S3_DELIMITER,
                                                    EncodingType="url",
                                                    MaxKeys=resolve_key_fetch_size(parameters),
                                                    Prefix=prefix,
                                                    ContinuationToken=continuation_token)

        # filter results from the s3 response
        if "CommonPrefixes" in s3_response:
            for item in s3_response["CommonPrefixes"]:
                key = item["Prefix"]
                if key != prefix:
                    keys.append(key)
        if "Contents" in s3_response:
            for item in s3_response["Contents"]:
                key = item["Key"]
                if key != prefix:
                    keys.append(key)

        # sort the keys, so we get the correct 'start_after' value
        keys.sort()

        # set the continuation token
        continuation_available = s3_response["IsTruncated"]
        continuation_token = s3_response["NextContinuationToken"] if "NextContinuationToken" in s3_response else None

        # check if we have reached the end of the results, and mark the last value to continue from, if available
        if len(keys) > max_keys_to_return:
            keys = keys[0:max_keys_to_return]
            new_start_after = keys[-1]
        elif len(keys) == max_keys_to_return and continuation_available:
            new_start_after = keys[-1]

    return keys, new_start_after


def resolve_start_after(parameters):
    return parameters[PARAMETER_START_AFTER] if PARAMETER_START_AFTER in parameters else None


def resolve_prefix(request):
    prefix = request['uri']
    prefix = prefix[1:] if prefix[0] == S3_DELIMITER else prefix
    return prefix


def resolve_max_keys_to_return(parameters):
    max_keys = int(parameters[PARAMETER_MAX_KEYS]) if PARAMETER_MAX_KEYS in parameters else MAX_KEYS
    max_keys = max(max_keys, 1)
    max_keys = min(max_keys, 1000)
    return max_keys


def resolve_key_fetch_size(parameters):
    return max(resolve_max_keys_to_return(parameters), MIN_KEYS_FETCH_SIZE)


def resolve_s3_bucket_name(request):
    return S3_BUCKET_NAME
