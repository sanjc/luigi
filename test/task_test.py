# -*- coding: utf-8 -*-
#
# Copyright 2012-2015 Spotify AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import doctest
import pickle

from helpers import unittest, LuigiTestCase
from datetime import datetime, timedelta

import luigi
import luigi.task
import luigi.util
from luigi.task_register import load_task


class DummyTask(luigi.Task):

    param = luigi.Parameter()
    bool_param = luigi.BoolParameter()
    int_param = luigi.IntParameter()
    float_param = luigi.FloatParameter()
    date_param = luigi.DateParameter()
    datehour_param = luigi.DateHourParameter()
    timedelta_param = luigi.TimeDeltaParameter()
    insignificant_param = luigi.Parameter(significant=False)


class DefaultInsignificantParamTask(luigi.Task):
    insignificant_param = luigi.Parameter(significant=False, default='value')
    necessary_param = luigi.Parameter(significant=False)


class TaskTest(unittest.TestCase):

    def test_tasks_doctest(self):
        doctest.testmod(luigi.task)

    def test_task_to_str_to_task(self):
        params = dict(
            param='test',
            bool_param=True,
            int_param=666,
            float_param=123.456,
            date_param=datetime(2014, 9, 13).date(),
            datehour_param=datetime(2014, 9, 13, 9),
            timedelta_param=timedelta(44),  # doesn't support seconds
            insignificant_param='test')

        original = DummyTask(**params)
        other = DummyTask.from_str_params(original.to_str_params())
        self.assertEqual(original, other)

    def test_task_from_str_insignificant(self):
        params = {'necessary_param': 'needed'}
        original = DefaultInsignificantParamTask(**params)
        other = DefaultInsignificantParamTask.from_str_params(params)
        self.assertEqual(original, other)

    def test_task_missing_necessary_param(self):
        with self.assertRaises(luigi.parameter.MissingParameterException):
            DefaultInsignificantParamTask.from_str_params({})

    def test_external_tasks_loadable(self):
        task = load_task("luigi", "ExternalTask", {})
        assert(isinstance(task, luigi.ExternalTask))

    def test_flatten(self):
        flatten = luigi.task.flatten
        self.assertEqual(sorted(flatten({'a': 'foo', 'b': 'bar'})), ['bar', 'foo'])
        self.assertEqual(sorted(flatten(['foo', ['bar', 'troll']])), ['bar', 'foo', 'troll'])
        self.assertEqual(flatten('foo'), ['foo'])
        self.assertEqual(flatten(42), [42])
        self.assertEqual(flatten((len(i) for i in ["foo", "troll"])), [3, 5])
        self.assertRaises(TypeError, flatten, (len(i) for i in ["foo", "troll", None]))

    def test_externalized_task_picklable(self):
        task = luigi.task.externalize(luigi.Task())
        pickled_task = pickle.dumps(task)
        self.assertEqual(task, pickle.loads(pickled_task))

    def test_no_unpicklable_properties(self):
        task = luigi.Task()
        task.set_tracking_url = lambda tracking_url: tracking_url
        task.set_status_message = lambda message: message
        with task.no_unpicklable_properties():
            pickle.dumps(task)
        self.assertIsNotNone(task.set_tracking_url)
        self.assertIsNotNone(task.set_status_message)
        tracking_url = task.set_tracking_url('http://test.luigi.com/')
        self.assertEqual(tracking_url, 'http://test.luigi.com/')
        message = task.set_status_message('message')
        self.assertEqual(message, 'message')


class ExternalizeTaskTest(LuigiTestCase):

    def test_externalize_taskclass(self):
        class MyTask(luigi.Task):
            def run(self):
                pass

        self.assertIsNotNone(MyTask.run)  # Assert what we believe
        task_object = luigi.task.externalize(MyTask)()
        self.assertIsNone(task_object.run)
        self.assertIsNotNone(MyTask.run)  # Check immutability
        self.assertIsNotNone(MyTask().run)  # Check immutability

    def test_externalize_taskobject(self):
        class MyTask(luigi.Task):
            def run(self):
                pass

        task_object = luigi.task.externalize(MyTask())
        self.assertIsNone(task_object.run)
        self.assertIsNotNone(MyTask.run)  # Check immutability
        self.assertIsNotNone(MyTask().run)  # Check immutability

    def test_externalize_taskclass_readable_name(self):
        class MyTask(luigi.Task):
            def run(self):
                pass

        task_class = luigi.task.externalize(MyTask)
        self.assertIsNot(task_class, MyTask)
        self.assertIn("MyTask", task_class.__name__)

    def test_externalize_taskclass_instance_cache(self):
        class MyTask(luigi.Task):
            def run(self):
                pass

        task_class = luigi.task.externalize(MyTask)
        self.assertIsNot(task_class, MyTask)
        self.assertIs(MyTask(), MyTask())  # Assert it have enabled the instance caching
        self.assertIsNot(task_class(), MyTask())  # Now, they should not be the same of course

    def test_externalize_same_id(self):
        class MyTask(luigi.Task):
            def run(self):
                pass

        task_normal = MyTask()
        task_ext_1 = luigi.task.externalize(MyTask)()
        task_ext_2 = luigi.task.externalize(MyTask())
        self.assertEqual(task_normal.task_id, task_ext_1.task_id)
        self.assertEqual(task_normal.task_id, task_ext_2.task_id)

    def test_externalize_same_id_with_task_namespace(self):
        # Dependent on the new behavior from spotify/luigi#1953
        class MyTask(luigi.Task):
            task_namespace = "something.domething"

            def run(self):
                pass

        task_normal = MyTask()
        task_ext_1 = luigi.task.externalize(MyTask())
        task_ext_2 = luigi.task.externalize(MyTask)()
        self.assertEqual(task_normal.task_id, task_ext_1.task_id)
        self.assertEqual(task_normal.task_id, task_ext_2.task_id)

    def test_externalize_with_requires(self):
        class MyTask(luigi.Task):
            def run(self):
                pass

        @luigi.util.requires(luigi.task.externalize(MyTask))
        class Requirer(luigi.Task):
            def run(self):
                pass

        self.assertIsNotNone(MyTask.run)  # Check immutability
        self.assertIsNotNone(MyTask().run)  # Check immutability
