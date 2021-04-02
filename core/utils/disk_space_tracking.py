import os
import subprocess
from abc import abstractmethod


class DiskSpaceTrackerMixin:
    """
    A Mixin that implements disk space tracking for Django models

    The target class should be a Django model (since the save(self) method is used)
    The target class should have a `used_space` model field, of type PositiveIntegerField
    The target class should provide a get_disk_path(self) method that returns the disk path that corresponds to the object

    Added methods
    -------
    update_disk_space():
        Updates the `used_space` field on the object to be the size of the folder returned by `get_disk_path()`.
    """
    used_space = None

    @abstractmethod
    def get_disk_path(self):
        raise NotImplementedError("get_disk_path() should be implemented!")

    # https://stackoverflow.com/a/4368431
    # This method is *supposed to* return exactly the same number as du -sb
    @staticmethod
    def _size_of_dir(path):
        total_size = os.path.getsize(path)
        for item in os.listdir(path):
            itempath = os.path.join(path, item)
            if os.path.isfile(itempath):
                # print(itempath, "=", os.path.getsize(itempath))  # Uncomment to print filename and size for every file
                total_size += os.path.getsize(itempath)
            elif os.path.isdir(itempath):
                total_size += DiskSpaceTrackerMixin._size_of_dir(itempath)
        return total_size

    def update_disk_space(self):
        # print("DISK SPACE", self) # Uncomment if debug info required
        self.used_space = DiskSpaceTrackerMixin._size_of_dir(self.get_disk_path()) // 1024
        self.save()  # this will call Flight.save() or UserProject.save()


class DiskRelationTrackerMixin:
    """
        A Mixin that implements related-model disk space tracking for Django models

        The target class should be a Django model (since the save(self) method is used)
        The target class should have a `used_space` model field, of type PositiveIntegerField
        The target class should provide a get_disk_related_models(self) method
        that returns an Iterable of all models that are included in this model's used space.
        All related models should have a `update_disk_space()` method  and a `used_space` property

        Added methods
        -------
        update_disk_space():
            Updates the `used_space` field on the object to be the sum of the disk spaces
            returned by all models in the `get_disk_related_models()` method.
    """
    used_space = None

    @abstractmethod
    def get_disk_related_models(self):
        raise NotImplementedError("get_disk_related_models() should be implemented!")

    def update_disk_space(self):
        # print("DISK SPACE USER", self) # Uncomment if debug info required
        # print(self.get_disk_related_models()) # Uncomment if debug info required
        self.used_space = sum([obj.used_space for obj in self.get_disk_related_models()])
        self.save()  # this will call User.save()
        # print("DISK SPACE USER", self, self.used_space)  # Uncomment if debug info required
