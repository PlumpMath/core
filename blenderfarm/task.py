
"""Task."""

import os

from . import db
from . import serializable

class TaskInfo(serializable.Serializable):

    """Contains data about a particular task."""

    def __init__(self, task):
        self.task = task

    def get_info_type(self):
        return "none"

    def unserialize(self, data):
        return self

    def serialize(self):
        return {}
    
    
class TaskInfoRender(TaskInfo):

    """`TaskInfo` containing render information"""

    def __init__(self, task):
        super().__init__(task)
        
        self.resolution = [1920, 1080]
        self.frame = 0

    def get_info_type(self):
        return "render"

    def unserialize(self, data):
        super().unserialize(data)

        self.resolution = data['resolution']
        self.frame = data['frame']

        return self

    def serialize(self):
        out = super().serialize()

        out['resolution'] = self.resolution
        out['frame'] = self.frame

        return out

    def get_result_filename(self):
        return os.path.join('result', self.task.job.job_id, str(self.frame) + '.png')
    
class Task(serializable.Serializable):

    """A single task, executed by render nodes."""

    # ## Statuses

    def __init__(self, job, task_info=None):
        # While `job` is a required argument, it might be `None` sometimes.
        
        self.job = job

        self.job_id = None

        if job:
            self.job_id = job.job_id

        # The `task_id` is unique to this `Job` and the task
        # itself. Each `Node` performing this `Task` will have the
        # same `task_id`; the only way to uniquely identify the output
        # of a single `Node` and `Task` combination is to use both
        # `node.node_id` and `task.task_id` at once.
        self.task_id = db.generate_uuid()

        # If `True`, this task will be ignored and never be completed.
        self.ignore = False

        self.complete = False

        self.in_progress = False

        self.task_info = task_info or None

        # A list of nodes that are currently processing this task.
        self.nodes_working = []

    def should_execute(self):
        """Whether or not this task should be executed. This is run once per
render node. Returns `True` if it can be executed, `False`
otherwise."""

        if self.complete:
            return False

        if self.in_progress:
            return False

        if self.ignore:
            return False

        return True

    def unserialize(self, data):
        super().unserialize(data)

        self.job_id = data['job_id']

        self.task_id = data['task_id']
        self.ignore = data['ignore']
        self.complete = data['complete']

        task_info_type = data['task_info_type']
        
        if task_info_type == 'render':
            self.task_info = TaskInfoRender(self)
        else:
            print("oh god we don't know what to do with a 'TaskInfo' of type '" + task_info_type + "'; things will break")
            return
            
        self.task_info.unserialize(data['task_info'])

        return self

    def serialize(self):
        # We specifically do not save `in_progress` because the render
        # node might have tried to upload the finished file while we
        # were offline. Instead, we re-render any frames that were
        # potentially in-progress when we were last shut down.
        
        out = super().serialize()

        out['job_id'] = self.job.job_id
        
        out['task_id'] = self.task_id
        out['ignore'] = self.ignore
        out['complete'] = self.complete
        
        out['task_info_type'] = self.task_info.get_info_type()
        out['task_info'] = self.task_info.serialize()

        return out

    def write_result(self, data):
        filename = self.task_info.get_result_filename()

        print('filename: ' + filename)

        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        
        with open(filename, 'wb') as handle:
            handle.write(data)
