import json
import os
import zipfile
from io import BytesIO

import botocore.session
from botocore.client import Config
from botocore.exceptions import ClientError

from .lbase import settings


class Manage:

    def __init__(self):
        self.aws_session = botocore.session.get_session()
        if settings.AWS_ACCESS_KEY and settings.AWS_SECRET_KEY:
            self.aws_session.set_credentials(
                access_key=settings.AWS_ACCESS_KEY,
                secret_key=settings.AWS_SECRET_KEY
            )
        config = Config(read_timeout=240)
        self.client = self.aws_session.create_client(
            'lambda', region_name=settings.AWS_REGION, config=config
        )

    def print_json(self, content):
        if isinstance(content, bytes):
            content = content.decode()
        print(json.dumps(content, indent=2))

    def print_response(self, response):
        self.print_json({k: v for k, v in response.items() if k != 'ResponseMetadata'})

    def lambda_status(self):
        response = self.client.get_account_settings()
        print("Account limit:")
        self.print_json(response['AccountLimit'])
        print("Account usage:")
        self.print_json(response['AccountUsage'])

    def function_status(self, fname):
        meta = self._function_meta(fname)
        print("Meta:")
        self.print_json(meta)

        try:
            response = self.client.get_function_configuration(FunctionName=fname)
            print('$LATEST version:')
            self.print_response(response)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print("{} function wasn't found.".format(fname))
            else:
                raise e

        response = self.client.list_versions_by_function(
            FunctionName=fname,
            MaxItems=100
        )

        print("Versions ({}):".format(len(response['Versions'])))
        for v in response['Versions']:
            print("- {}".format(v['Version']))

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
            'description': "No description",
            'binaries': None
        }

        default_meta.update(meta)
        default_meta['local_path'] = path
        return default_meta

    def _create_zip(self, fname, meta):
        path = rel(fname)
        io = BytesIO()
        print("Zipping ...")

        if meta['binaries']:
            assert meta['binaries'].startswith('s3://')
            bucket = meta['binaries'].split('/')[2]
            key = '/'.join(meta['binaries'].split('/')[3:])
            # calculate local binaries etag
            etag = ""
            bin_file = rel('bin/{}.zip'.format(fname))
            if os.path.isfile(bin_file):
                with open(bin_file, 'rb') as f:
                    etag = calculate_etag(f)

            print("Etag: {}".format(etag))

            s3_client = self.aws_session.create_client('s3', region_name=settings.AWS_REGION)
            try:
                response = s3_client.get_object(
                    Bucket=bucket,
                    IfNoneMatch=etag,
                    Key=key
                )

                io = BytesIO(response['Body'].read())
                with open(bin_file, 'wb') as f:
                    f.write(io.read())
                io.seek(0)
            except ClientError as e:
                if e.response['Error']['Code'] == '304':
                    print("Skip binaries download: no changes.")
                    with open(bin_file, 'rb') as f:
                        io = BytesIO(f.read())
                else:
                    raise e

        with zipfile.ZipFile(io, 'a', zipfile.ZIP_DEFLATED) as f:
            for root, dirs, files in os.walk(path):
                for file in files:
                    path = os.path.join(root, file)
                    arcpath = path[path.rindex('/{}/'.format(fname)) + len(fname) + 2:]
                    print("- {}".format(arcpath))
                    to_skip = (
                        arcpath.lower() in ('lmeta.json', '.ds_store', 'readme.md') or
                        '__pycache__' in arcpath or
                        arcpath.endswith('.pyc')
                    )
                    if to_skip:
                        print('Skip {}'.format(file))
                        continue
                    f.write(path, arcname=arcpath)
        io.seek(0)
        return io

    def _function_create(self, fname):
        meta = self._function_meta(fname)
        zip_file = self._create_zip(fname, meta)

        response = self.client.create_function(
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

        self.print_response(response)

    def _function_code_update(self, fname):
        meta = self._function_meta(fname)
        zip_file = self._create_zip(fname, meta)
        response = self.client.update_function_code(
            FunctionName=fname,
            ZipFile=zip_file.read(),
            Publish=True
        )
        self.print_response(response)

    def function_update(self, fname):
        meta = self._function_meta(fname)
        response = self.client.update_function_configuration(
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

        self.print_response(response)

    def function_deploy(self, fname):
        exist = True
        try:
            self.client.get_function_configuration(FunctionName=fname)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                exist = False
        if exist:
            print("Updating {} function.".format(fname))
            self._function_code_update(fname)
        else:
            print("Creating {} function.".format(fname))
            self._function_create(fname)

    def function_list(self):
        response = self.client.list_functions(MaxItems=100)
        print("Functions:")
        for f in response['Functions']:
            try:
                self._function_meta(fname=f['FunctionName'])
            except AssertionError:
                continue
            print("- {name}: {version}".format(name=f['FunctionName'], version=f['Version']))

    def function_invoke(self, fname, args):
        self._function_meta(fname=fname)
        response = self.client.invoke(
            FunctionName=fname,
            InvocationType='RequestResponse',
            LogType='None',
            Payload=args.encode('utf-8'),
            Qualifier='$LATEST'
        )
        self.print_json(response['Payload'].read())

    def function_delete(self, fname, version):
        response = self.client.delete_function(
            FunctionName=fname,
            Qualifier=version
        )
        self.print_response(response)

    def alias_list(self, fname):
        response = self.client.list_aliases(
            FunctionName=fname,
            MaxItems=100
        )
        self.print_response(response)

    def alias_use(self, fname, aname, version):
        description = "{fname}:{aname} -> {fname}:{version}".format(fname=fname, version=version, aname=aname)
        try:
            response = self.client.update_alias(
                FunctionName=fname,
                Name=aname,
                FunctionVersion=version,
                Description=description
            )
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise e
            else:
                print(
                    "Creating {fname}:{version} -> {aname} alias ...".format(
                        fname=fname,
                        version=version,
                        aname=aname
                    )
                )
                response = self.client.create_alias(
                    FunctionName=fname,
                    Name=aname,
                    FunctionVersion=version,
                    Description=description
                )

        self.print_response(response)

    def alias_delete(self, fname, aname):
        response = self.client.delete_alias(
            FunctionName=fname,
            Name=aname
        )
        self.print_response(response)

    def alias_status(self, fname, aname):
        response = self.client.get_alias(
            FunctionName=fname,
            Name=aname
        )
        self.print_response(response)


def main(entity, command, *arguments):
    manage = Manage()
    getattr(manage, '{}_{}'.format(entity, command))(*arguments)
