from dspyce.metadata.models import MetaData, MetaDataValue


class DSpaceObject:
    """
    The class DSpaceObject represents an Object in a DSpace repository, such as Items, Collections, Communities.
    """

    uuid: str
    """The uuid of the DSpaceObject"""
    name: str
    """The name of the DSpaceObject, if existing"""
    handle: str
    """The handle of the Object"""
    metadata: MetaData
    """The metadata provided for the object."""
    statistic_reports: dict
    """A dictionary of statistic report objects."""

    def __init__(self, uuid: str = '', handle: str = '', name: str = ''):
        """
        Creates a new object of the class DSpaceObject

        :param uuid: The uuid of the DSpaceObject. Default is ''
        :param handle: The handle of the DSpaceObject. Default is ''
        :param name: The name of the DSpaceObject, if existing.
        """
        self.uuid = uuid
        self.handle = handle
        self.name = name
        self.metadata = MetaData({})
        self.statistic_reports = {}

    def add_metadata(self, tag: str, value: str, language: str = None):
        """
        Creates a new metadata field with the given value.

        :param tag: The correct metadata tag. The string must use the format <schema>.<element>.<qualifier>.
        :param value: The value of the metadata-field.
        :param language: The language of the metadata field.

        :raises KeyError: If the metadata tag doesn't use the format <schema>.<element>.<qualifier>.'
        """
        self.metadata[tag] = MetaDataValue(value, language)

    def remove_metadata(self, tag: str, value: str = None):
        """
        Remove a specific metadata field from the DSpaceObject. Can either be all values for a field or ony a specific
        value based on the *value* parameter.

        :param tag: The correct metadata tag. The string must use the format <schema>.<element>.<qualifier>.
        :param value: The value of the metadata field to delete. Can be used, if only one value in a list of values
            should be deleted. If None, all values from the given tag will be deleted.
        """
        if value is None:
            self.metadata.pop(tag)
        else:
            self.metadata[tag] = list(filter(lambda x: x.value != value, self.metadata[tag]))

    def replace_metadata(self, tag: str, value: str, language: str = None):
        """
        Replaces a specific metadata field from the DSpaceObject. Replaces all values of a given tag.

        :param tag: The correct metadata tag. The string must use the format <schema>.<element>.<qualifier>.
        :param value: The value of the metadata field to add. Can be used, if only one value in a list of values
            should be deleted. If None, all values from the given tag will be deleted.
        :param language: The language of the metadata value to add.
        """
        self.remove_metadata(tag)
        self.add_metadata(tag, value, language)

    def move_metadata(self, tag: str, from_position: int, to_position: int):
        """
        Moves the MetadataValue object from the given postion to the given "to_position" position.
        :param tag: The metadata tag.
        :param from_position: The original position of the metadata value to move.
        :param to_position: The new position of the metadata value to move (-1 to move it at the end of the array).
        :raises KeyError: If the from_position doesn't exist in the object's metadata.
        :raises IndexError: If the to_position is higher than the length of the metadataValue list.
        """
        md = self.get_metadata(tag)
        if len(md) == 0 or from_position >= len(md):
            raise KeyError('The position of the metadata value to move is out of range or the MetadataValue does not'
                           'exist')
        if to_position >= len(md) or to_position <= (len(md)*-1):
            raise IndexError('The target position of the MetadataValue to move is out of range for the metadata list.')
        value = md.pop(from_position)
        md = md[:to_position] + [value] + md[to_position:]
        self.metadata[tag] = md


    def get_dspace_object_type(self) -> str:
        """
        This Function serves mainly to be overwritten by subclasses to get the type of DSpaceObject.
        """
        pass

    def get_identifier(self) -> str | None:
        """
        Returns the identifier of this object. Preferably this will be the uuid, but if this does not exist, it uses
        the handle.
        :return: The identifier as a string.
        """
        if self.uuid != '':
            return self.uuid
        if self.handle != '':
            return self.handle
        return None

    def __eq__(self, other):
        if self.uuid == '' and other.uuid == '' and self.handle == '' and other.handle == '':
            raise ValueError('Can not compare objects without a uuid or handle.')
        return (self.uuid == other.uuid) if self.uuid != '' else (self.handle == other.handle)

    def __str__(self):
        return f'DSpace object with the uuid {self.uuid}:\n\t' + '\n\t'.join(str(self.metadata).split('\n'))

    def to_dict(self) -> dict:
        """
            Converts the current item object to a dictionary object containing all available metadata.
        """
        obj_dict = {}
        if self.uuid != '':
            obj_dict['uuid'] = self.uuid
        if self.handle != '':
            obj_dict['handle'] = self.handle
        if self.name != '':
            obj_dict['name'] = self.name
        if self.get_dspace_object_type() is not None:
            obj_dict['type'] = self.get_dspace_object_type().lower()
        obj_dict['metadata'] = self.metadata.to_dict()
        return obj_dict

    def has_metadata(self, tag: str) -> bool:
        """
        Checks whether this object has a specific metadata field.
        :param tag: The metadata tag to check.
        :returns: True if the metadata field exists, False otherwise.
        """
        return tag in self.metadata.keys()

    def get_metadata(self, tag: str) -> list[MetaDataValue]:
        """
        Retrieves a list of MetadataValue objects for the given tag.
        :param tag: The tag to get the metadata for.
        :return: A list of MetadataValue objects.
        """
        md = self.metadata.get(tag)
        return [] if md is None else md

    def get_metadata_values(self, tag: str) -> list | None:
        """
        Retrieves the metadata values of a specific tag as a list.

        :param tag: The metadata tag: prefix.element.qualifier
        :return: The values as a list or None, if the tag doesn't exist.
        """
        m = self.get_metadata(tag)
        return [v.value for v in m] if len(m) > 0 else None

    def get_first_metadata(self, tag: str) -> MetaDataValue | None:
        """
        Retrieve the first metadata value of a specific metadata field.
        """
        md = self.get_metadata(tag)
        return md[0] if len(md) > 0 else None


    def get_first_metadata_value(self, tag: str) -> str | None:
        """
        Retrieve the first metadata value of a specific metadata field.
        """
        return self.get_metadata_values(tag)[0] if self.get_metadata_values(tag) is not None else None

    def add_statistic_report(self, report: dict | list[dict] | None):
        """
        Adds a new report or list of reports as a dict object to the DSpaceObject

        :param report: The report(s) to add.
        """
        if report is None:
            return
        report = [report] if isinstance(report, dict) else report
        for r in report:
            for k in r.keys():
                if k not in self.statistic_reports.keys():
                    self.statistic_reports[k] = r[k]
                else:
                    if isinstance(r[k], dict):
                        self.statistic_reports[k] = (self.statistic_reports[k] +
                                                     [r[k]]) if isinstance(self.statistic_reports[k],
                                                                           list) else [self.statistic_reports[k], r[k]]
                    else:
                        self.statistic_reports[k] = r[k]

    def has_statistics(self) -> bool:
        """
        Checks if statistic reports are available for this object.

        :return: True if there is at least one report.
        """
        return len(self.statistic_reports.keys()) > 0
