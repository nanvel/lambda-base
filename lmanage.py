#!.venv/bin/python
import base64
import json
import os
import sys
import zipfile
from io import BytesIO

from botocore.exceptions import ClientError

from lbase.client import client
from lbase.utils.path import rel


class Manage:

    def __init__(self):
        pass

    def lambda_status(self):
        response = client.get_account_settings()
        print(json.dumps(response['AccountLimit'], indent=2))
        print(json.dumps(response['AccountUsage'], indent=2))

    def function_status(self, fname):
        meta = self._function_meta(fname)

        try:
            response = client.get_function_configuration(FunctionName=fname)
            print(response)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print("{} function wasn't found.".format(fname))
            else:
                raise e

    def _function_meta(self, fname):
        assert fname.startswith('lambda_')
        path = rel('{}/lmeta.json'.format(fname))
        with open(path, 'r') as f:
            meta = json.loads(f.read())

        default_meta = {
            'runtime': 'python3.6',
            'handler': 'lambda_function.lambda_handler',
            'vpc_config': {},
            'timeout': 3,
            'memory': 128,
            'env_variables': {},
            'tags': {},
            'role': '',
            'description': "No description"
        }

        default_meta.update(meta)
        default_meta['local_path'] = path
        return default_meta

    def _create_zip(self, path):
        io = BytesIO()
        print("Zipping ...")
        with zipfile.ZipFile(io, 'w', zipfile.ZIP_DEFLATED) as f:
            for root, dirs, files in os.walk(path):
                for file in files:
                    if root.find('/') == -1 and file in ('meta.json',):
                        print('Skip {}'.format(file))
                        continue
                    print(root, file)
                    f.write(os.path.join(root, file))
        io.seek(0)
        return io

    def _function_create(self, fname):
        meta = self._function_meta(fname)
        zip_file = self._create_zip(fname)

        response = client.create_function(
            FunctionName=fname,
            Runtime=meta['runtime'],
            Role=meta['role'],
            Handler=meta['handler'],
            Code={'ZipFile': zip_file.read()},
            Description=meta['description'],
            Timeout=meta['timeout'],
            MemorySize=meta['memory'],
            Publish=True,
            VpcConfig=meta['vpc_config'],
            Environment={'Variables': meta['env_variables']},
            Tags=meta['tags']
        )

        print(response)

    def _function_code_update(self, fname):
        meta = self._function_meta(fname)
        zip_file = self._create_zip(fname)
        client.update_function_code(
            FunctionName=fname,
            ZipFile=zip_file.read(),
            Publish=True
        )

    def function_update(self, fname):
        meta = self._function_meta(fname)
        response = client.update_function_configuration(
            FunctionName=fname,
            Role=meta['role'],
            Handler=meta['handler'],
            Description=meta['description'],
            Timeout=meta['timeout'],
            MemorySize=meta['memory'],
            VpcConfig=meta['vpc_config'],
            Environment={'Variables': meta['env_variables']},
            Runtime=meta['runtime']
        )

        print(response)

    def function_deploy(self, fname):
        exist = True
        try:
            response = client.get_function_configuration(FunctionName=fname)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                exist = False
        if exist:
            print("Updating {} function.".format(fname))
            self._function_code_update(fname)
        else:
            print("Creating {} function.".format(fname))
            self._function_create(fname)

    def alias_status(self):
        pass

    def function_list(self):
        response = client.list_functions(
            FunctionVersion='ALL',
            MaxItems=100
        )
        print([(f['FunctionName'], f['Version']) for f in response['Functions']])

    def function_invoke(self, fname, args):
        response = client.invoke(
            FunctionName=fname,
            InvocationType='RequestResponse',
            LogType='None',
            Payload=json.dumps({'a': 1}).encode('utf-8'),
            Qualifier='$LATEST'
        )
        print(response['Payload'].read())


if __name__ == '__main__':
    _, entity, command, *arguments = sys.argv

    manage = Manage()
    result = getattr(manage, '{}_{}'.format(entity, command))(*arguments)
