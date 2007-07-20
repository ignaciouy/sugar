# Copyright (C) 2007, One Laptop Per Child
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import logging
from datetime import datetime
import os

import gobject

from sugar.datastore import dbus_helpers
from sugar import activity
from sugar.activity.bundle import Bundle
from sugar.activity import activityfactory
from sugar.activity.activityhandle import ActivityHandle

class DSMetadata(gobject.GObject):
    __gsignals__ = {
        'updated': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                    ([]))
    }

    def __init__(self, props=None):
        gobject.GObject.__init__(self)
        if not props:
            self._props = {}
        else:
            self._props = props
        
        default_keys = ['activity', 'activity_id',
                        'mime_type', 'title_set_by_user']
        for key in default_keys:
            if not self._props.has_key(key):
                self._props[key] = ''

    def __getitem__(self, key):
        return self._props[key]

    def __setitem__(self, key, value):
        if not self._props.has_key(key) or self._props[key] != value:
            self._props[key] = value
            self.emit('updated')

    def __delitem__(self, key):
        del self._props[key]

    def has_key(self, key):
        return self._props.has_key(key)
    
    def get_dictionary(self):
        return self._props

class DSObject(object):
    def __init__(self, object_id, metadata=None, file_path=None):
        self.object_id = object_id
        self._metadata = metadata
        self._file_path = file_path
        self._destroyed = False
        self._owns_file = False

    def get_metadata(self):
        if self._metadata is None and not self.object_id is None:
            metadata = DSMetadata(dbus_helpers.get_properties(self.object_id))
            self._metadata = metadata
        return self._metadata
    
    def set_metadata(self, metadata):
        if self._metadata != metadata:
            self._metadata = metadata

    metadata = property(get_metadata, set_metadata)

    def get_file_path(self):
        if self._file_path is None and not self.object_id is None:
            self.set_file_path(dbus_helpers.get_filename(self.object_id))
            self._owns_file = True
        return self._file_path
    
    def set_file_path(self, file_path):
        if self._file_path != file_path:
            if self._file_path and self._owns_file:
                if os.path.isfile(self._file_path):
                    os.remove(self._file_path)
                self._owns_file = False
            self._file_path = file_path

    file_path = property(get_file_path, set_file_path)

    def get_activities(self):
        activities = []

        if self.metadata['activity']:
            activity_info = activity.get_registry().get_activity(self.metadata['activity'])
            activities.append(activity_info)

        mime_type = self.metadata['mime_type']
        if mime_type:
            activities_info = activity.get_registry().get_activities_for_type(mime_type)
            for activity_info in activities_info:
                if activity_info.service_name != self.metadata['activity']:
                    activities.append(activity_info)

        return activities

    def is_bundle(self):
        return self.metadata['mime_type'] == 'application/vnd.olpc-x-sugar'

    def resume(self):
        if self.is_bundle():
            bundle = Bundle(self.file_path)
            if not bundle.is_installed():
                bundle.install()

            activityfactory.create(bundle.get_service_name())
        else:
            service_name = self.get_activities()[0].service_name

            activity_id = self.metadata['activity_id']
            object_id = self.object_id

            if activity_id:
                handle = ActivityHandle(object_id=object_id,
                                        activity_id=activity_id)
                activityfactory.create(service_name, handle)
            else:
                activityfactory.create_with_object_id(service_name, object_id)

    def destroy(self):
        logging.debug('DSObject.destroy() file_path: %r.' % self._file_path)
        if self._destroyed:
            logging.warning('This DSObject has already been destroyed!.')
            import pdb;pdb.set_trace()
            return
        self._destroyed = True
        if self._file_path and self._owns_file:
            logging.debug('Removing temp file: %r' % self._file_path)
            if os.path.isfile(self._file_path):
                os.remove(self._file_path)
            self._owns_file = False
        self._file_path = None

    def __del__(self):
        if not self._destroyed:
            logging.warning('DSObject was deleted without cleaning up first. ' \
                            'Please call DSObject.destroy() before disposing it.')
            self.destroy()

def get(object_id):
    logging.debug('datastore.get')
    metadata = dbus_helpers.get_properties(object_id)
    file_path = dbus_helpers.get_filename(object_id)

    ds_object = DSObject(object_id, DSMetadata(metadata), file_path)
    # TODO: register the object for updates
    return ds_object

def create():
    metadata = DSMetadata()
    metadata['ctime'] = datetime.now().isoformat()
    metadata['mtime'] = metadata['ctime']
    return DSObject(object_id=None, metadata=metadata, file_path=None)

def write(ds_object, update_mtime=True, reply_handler=None, error_handler=None):
    logging.debug('datastore.write')

    properties = ds_object.metadata.get_dictionary().copy()

    if update_mtime:
        properties['mtime'] = datetime.now().isoformat()

    if ds_object.object_id:
        dbus_helpers.update(ds_object.object_id,
                            properties,
                            ds_object.file_path,
                            reply_handler=reply_handler,
                            error_handler=error_handler)
    else:
        ds_object.object_id = dbus_helpers.create(properties,
                                                  ds_object.file_path)
        # TODO: register the object for updates
    logging.debug('Written object %s to the datastore.' % ds_object.object_id)

def delete(object_id):
    logging.debug('datastore.delete')
    dbus_helpers.delete(object_id)

def find(query, sorting=None, limit=None, offset=None, reply_handler=None,
         error_handler=None):
    if sorting:
        query['order_by'] = sorting
    if limit:
        query['limit'] = limit
    if offset:
        query['offset'] = offset
    
    props_list, total_count = dbus_helpers.find(query, reply_handler, error_handler)
    
    objects = []
    for props in props_list:
        if props.has_key('filename') and props['filename']:
            file_path = props['filename']
            del props['filename']
        else:
            file_path = None

        object_id = props['uid']
        del props['uid']

        ds_object = DSObject(object_id, DSMetadata(props), file_path)
        objects.append(ds_object)

    return objects, total_count

def mount(uri, options):
    return dbus_helpers.mount(uri, options)

def unmount(mount_point_id):
    dbus_helpers.unmount(mount_point_id)

def mounts():
    return dbus_helpers.mounts()

def get_unique_values(key):
    return dbus_helpers.get_unique_values(key)
