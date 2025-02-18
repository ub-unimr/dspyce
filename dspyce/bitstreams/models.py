import os
import re
import requests

import warnings
from io import BytesIO
from dspyce.models import DSpaceObject
from PIL import Image

class Bitstream(DSpaceObject):
    """
        A class for managing bitstream files in the DSpace context.
    """
    file_name: str
    """The name of the file."""
    path: str
    """The path, where the file can be found."""
    permissions: list[dict[str, str]]
    """Permission which group shall have access to this file."""
    show: bool
    """If the file should be accessible for users or only provides information for the item import."""
    bundle: any
    """The bundle where to store the file. The default is set to the variable DEFAULT_BUNDLE."""
    primary: bool
    """If the bitstream shall be the primary bitstream for the item."""
    size_bytes: int
    """The size of the Bitstream in bytes."""
    check_sum: str
    """The checksum of the Bitstream."""

    def __init__(self, name: str, path: str, bundle: any = None, uuid: str = None, primary: bool = False,
                 size_bytes: int = None, check_sum: str = None):
        """
        Creates a new Bitstream object.
        :param name: The name of the bitstream.
        :param path: The path, where the file is currently stored.
        :param bundle: The bundle, where the bitstream should be placed in. The default is ORIGINAL.
        :param uuid: The uuid of the bitstream if existing.
        :param primary: Primary is used to specify the primary bitstream.
        :param size_bytes: The size of the bitstream in bytes.
        :param check_sum: The checksum of the bitstream.
        """
        self.file_name = name
        self.path = path
        self.path += '/' if len(self.path) > 0 and self.path[-1] != '/' else ''
        self.permissions = []
        self.bundle = bundle
        self.primary = primary
        self.size_bytes = size_bytes
        self.check_sum = check_sum
        super().__init__(uuid, '', name)
        if name != '':
            self.add_metadata('dc.title', name)

    def __str__(self):
        """
        Provides all information about the DSpace-Content file.

        :return: A SAF-ready information string which can be used for the content-file.
        """
        export_name = self.file_name
        if self.bundle is not None:
            export_name += f'\tbundle:{self.bundle.name}'
        if self.get_description() is not None:
            export_name += f'\tdescription:{self.get_description()}'
        if len(self.permissions) > 0:
            for p in self.permissions:
                export_name += f'\tpermissions:-{p["type"]} \'{p["group"]}\''
        if self.primary:
            export_name += '\tprimary:true'
        return export_name

    def get_description(self):
        """
        Returns the current description of the current bitstream.
        """
        return self.get_first_metadata_value('dc.description')

    def add_description(self, description: str, language: str = None):
        """
            Creates a description to the content-file.

            :param description: String which provides the description.
            :param language: The language of the description.
        """
        self.add_metadata('dc.description', description, language)

    def add_permission(self, rw: str, group_name: str):
        """
            Add access information to the Bitstream.

            :param rw: Access-type r-read, w-write.
            :param group_name: Group to which the access will be provided.
        """
        if rw not in ('r', 'w'):
            raise ValueError(f'Permission type must be "r" or "w". Got {rw} instead!')
        self.permissions.append({'type': rw, 'group': group_name})

    def get_bitstream_file(self, timeout: int = 30) -> bytes:
        """
        Returns the actual file as a TextIOWrapper object.

        :param timeout: The connection timeout for reading bitstreams from remote resources.
        """
        if self.is_remote_resource():
            return requests.get(self.path, timeout=timeout).content
        with open(self.path + self.file_name, 'rb') as f:
            return f.read()

    def save_bitstream(self, path: str, timeout: int = 30):
        """
        Saves the current bitstream to the given path.

        :param path: The path where the bitstream file is to be saved.
        :param timeout: The connection timeout for reading bitstreams from remote resources.
        :raises FileExistsError: if the file already exists in the given path.
        """
        if self.file_name in os.listdir(path):
            raise FileExistsError(f'The file "{self.file_name}" already exists in {path}')
        file = self.get_bitstream_file(timeout)
        if isinstance(file, str):
            file = file.encode('utf-8')
        with open(f'{path}/{self.file_name}', 'wb') as f:
            f.write(file)

    def __eq__(self, other):
        """
        Checks if two content files are equal based on their name and path (and possible uuid).
        
        :param other: The other object to compare with.
        :raises TypeError: if the type of "other" is not Bitstream
        """
        if not isinstance(other, Bitstream):
            raise TypeError(f'Can not compare Bitstream with type({type(other)})')
        return (self.file_name == other.file_name and
                self.path == other.path and
                ((self.uuid is None or other.uuid is None) or self.uuid == other.uuid))

    def get_dspace_object_type(self) -> str:
        """
        Return the DSpaceObject type for the bitstream object, aka "Bitstream"
        """
        return 'Bitstream'

    def get_identifier(self) -> str | None:
        """
        Overwrites the standard DSpace-Object get_identifier method: only returns uuid for bitstreams (no handles
        allowed)
        """
        return self.uuid

    def to_dict(self) -> dict:
        """
        Returns a dictionary representation of the bitstream object.
        """
        obj_dict = super().to_dict()
        if self.bundle is not None and self.bundle.name != '':
            obj_dict['bundleName'] = self.bundle.name
        return obj_dict

    def set_size(self, size: int = None):
        """
        Sets the size of the bitstream. If parameter size is None, this method is calculating the size of the Bitstream.
        :param size: The size of the bitstream.
        """
        if size is None:
            if self.is_remote_resource():
                headers = requests.head(self.path).headers
                if 'Content-Length' in headers:
                    self.size_bytes = int(headers['Content-Length'])
                else:
                    raise requests.exceptions.InvalidHeader('Did not get "Content-Length key in the header."')
            else:
                self.size_bytes = os.path.getsize(self.path)
        else:
            self.size_bytes = size

    def is_remote_resource(self) -> bool:
        """
        Checks if the resources should be retrieved from an url.
        :return: True if the path starts with http(s)?://
        """
        return re.search(r'^http(s)?://', self.path) is not None


class IIIFBitstream(Bitstream):
    """
        A class for managing iiif-specific content files in the saf-packages.
    """

    def __init__(self, name: str, path: str, bundle: any = None, uuid: str = None, primary: bool = False,
                 size_bytes: int = None, check_sum: str = None):
        """
        Creates a new IIIF-Bitstream object.

        :param name: The name of the bitstream.
        :param path: The path, where the file is currently stored.
        :param bundle: The bundle, where the bitstream should be placed in. The default is ORIGINAL.
        :param uuid: The uuid of the bitstream if existing.
        :param primary: Primary is used to specify the primary bitstream.
        :param size_bytes: The size of the bitstream in bytes.
        :param check_sum: The checksum of the bitstream.
        """
        super().__init__(name, path, bundle, uuid, primary, size_bytes, check_sum)

    def __str__(self):
        """
        Provides all information about the DSpace IIIF-Content file.

        :return: A SAF-ready information string which can be used for the content-file.
        """
        export_name = super().__str__()
        if len(self.iiif.keys()) > 0:
            export_name += (f'\tiiif-label:{self.get_iiif_label()}'
                            f'\tiiif-toc:{self.get_iiif_toc()}'
                            f'\tiiif-width:{self.get_first_metadata_value('iiif.image.width')}'
                            f'\tiiif-height:{self.get_first_metadata_value('iiif.image.height')}')
        else:
            warnings.warn('You are about to generate information of IIIF-specific DSpace bitstream, without providing'
                          'IIIF-specific information. Are you sure, you want to do this?')
        return export_name

    def add_iiif(self, label: str, toc: str, w: int = 0):
        """
            Add  IIIF-information for the bitstream.

            :param label: is the label that will be used for the image in the viewer.
            :param toc: is the label that will be used for a table of contents entry in the viewer.
            :param w: is the image width to reduce it. Default 0
        """
        img = Image.open(BytesIO(self.get_bitstream_file()))
        width, height = img.size
        if w != 0 and w < width:
            scale = int(width/w)
            super().file = img.reduce(scale).tobytes()
        img.close()
        self.add_metadata('iiif.label', label)
        self.add_metadata('iiif.toc', toc)
        self.add_metadata('iiif.image.width', str(width))
        self.add_metadata('iiif.image.height', str(height))

    def get_iiif_label(self) -> str | None:
        """
        Returns the label of the IIIF bitstream.
        """
        return self.get_first_metadata_value('iiif.label')

    def get_iiif_toc(self) -> str | None:
        """
        Returns the toc label of the IIIF bitstream.
        """
        return self.get_first_metadata_value('iiif.toc')

    def get_bitstream_size(self) -> tuple[float, float] | None:
        """
        Returns the size (width, height) of a given bitstream as a tuple of float values.
        """
        if (self.get_first_metadata_value('iiif.image.width') is not None and
            self.get_first_metadata_value('iiif.image.height') is not None):
            return (float(self.get_first_metadata_value('iiif.image.width')),
                    float(self.get_first_metadata_value('iiif.image.height')))
        return None


class Bundle(DSpaceObject):
    """
    The class Bundle represents a bundle in the DSpace context. I can contain several bitstreams.
    """

    DEFAULT_BUNDLE: str = 'ORIGINAL'
    """The default bundle name."""
    bitstreams: list[Bitstream]
    """A list of bitstream associated with the bundle"""

    def __init__(self, name: str = DEFAULT_BUNDLE, description: str = '', uuid: str = None,
                 bitstreams: list[Bitstream] = None):
        """
        Creates a new bundle object.

        :param name: The bundle name.
        :param description: A description if existing.
        :param uuid: The uuid of the bundle, if known.
        :param bitstreams: A list of bitstreams associated with this bundle.
        :raises AttributeError: If the bundle name is not of type <str> or is empty and no uuid is provided.
        """
        if not isinstance(name, str) or (name.strip() == '' and uuid is None):
            raise AttributeError('You have to provide a correct bundle name expected not-empty string,'
                                 f'but got "{name}".')
        super().__init__(uuid, '', name)
        if description != '':
            self.add_metadata('dc.description', description)
        if name != '':
            self.add_metadata('dc.title', name)
        self.bitstreams = []
        if bitstreams is not None:
            [self.add_bitstream(b) for b in bitstreams]

    def __str__(self):
        return ('Bundle - {}{}:\n{}'.format(self.name,
                                            f'({self.uuid})' if self.uuid is not None else '',
                                            '\n'.join([f'\t{i}' for i in self.bitstreams])))

    def __eq__(self, other) -> bool:
        """
        Check if two bundle objects are equal

        :param other: The other bundle object to compare with.
        :return: True, if the two bundles have the same name.
        """
        if not isinstance(other, Bundle):
            raise TypeError(f'Can not compare type Bundle to "{type(other)}"')
        if self.uuid is None or other.uuid is None:
            return self.name == other.name

        return self.uuid == other.uuid and self.name == other.name

    def get_bitstreams(self, filter_condition=lambda x: True) -> list[Bitstream]:
        """
        Returns a list of bitstreams in this bundle, filtered by a filter defined in filter_condition.

        :param filter_condition: A condition to filter the bitstreams returned.
        :return: A list of Bitstream objects.
        """
        return list(filter(filter_condition, self.bitstreams))

    def add_bitstream(self, bitstream: Bitstream):
        """
        Adds a bitstream to this bundle.

        :param bitstream: The bitstream to add.
        """
        bitstream.bundle = self
        self.bitstreams.append(bitstream)

    def remove_bitstream(self, bitstream: Bitstream):
        """
        Removes a bitstream from the current bundle. Raises an Exception if the bitstream does not exist.

        :param bitstream: The bitstream to remove from the bundle.
        :raises FileNotFoundError: If the bitstream does not exist.
        """
        self.bitstreams.remove(bitstream)

    def save_bitstreams(self, path: str):
        """
        Saves the bitstreams of the given bundle into path.

        :param path: The path where to save the bitstreams.
        :raises FileExistsError: If the Bitstream already exists in the given path.
        """
        for b in self.bitstreams:
            b.save_bitstream(path)

    def get_description(self) -> str:
        """
        Returns the description of this bundle.
        """
        return self.get_first_metadata_value('dc.description')

    def get_dspace_object_type(self) -> str:
        """
        Returns the DSpaceObject type, aka. "Bundle".
        """
        return 'Bundle'
