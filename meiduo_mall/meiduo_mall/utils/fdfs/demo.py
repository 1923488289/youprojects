from fdfs_client.client import Fdfs_client

if __name__ == '__main__':
    client = Fdfs_client('client.conf')
    ret = client.upload_by_filename('/home/python/Desktop/1.jpg')
    print(ret)
    '''
    {
        'Storage IP': '192.168.47.128',
        'Status': 'Upload successed.',
        'Group name': 'group1',
        'Local file name': '/home/python/Desktop/1.jpg',
        'Uploaded size': '8.00KB',
        'Remote file_id': 'group1/M00/00/00/wKgvgFzOp4mAVDGLAAAhg8MeEWU417.jpg'
    }
    '''
