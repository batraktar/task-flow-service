import uuid
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from tasks.models import Task


class TaskModelTests(TestCase):
    def test_create_task(self):
        task = Task.objects.create(
            title='Finish test task',
            description='Implement CRUD API',
            status=Task.TaskStatus.TODO,
            priority=3,
            due_date=timezone.localdate() + timedelta(days=2),
        )

        self.assertIsNotNone(task.id)
        self.assertEqual(task.title, 'Finish test task')
        self.assertEqual(task.status, Task.TaskStatus.TODO)
        self.assertEqual(task.priority, 3)

    def test_priority_validation(self):
        task = Task(
            title='Invalid priority',
            status=Task.TaskStatus.TODO,
            priority=10,
        )

        with self.assertRaises(ValidationError) as error:
            task.full_clean()

        self.assertIn('priority', error.exception.message_dict)

    def test_due_date_validation(self):
        task = Task(
            title='Past due date',
            status=Task.TaskStatus.TODO,
            priority=2,
            due_date=timezone.localdate() - timedelta(days=1),
        )

        with self.assertRaises(ValidationError) as error:
            task.full_clean()

        self.assertIn('due_date', error.exception.message_dict)


class TaskAPITests(APITestCase):
    def setUp(self):
        self.list_url = reverse('task-list')
        self.task = Task.objects.create(
            title='Existing task',
            description='Base object for tests',
            status=Task.TaskStatus.TODO,
            priority=3,
            due_date=timezone.localdate() + timedelta(days=2),
        )

    def test_create_task_success(self):
        payload = {
            'title': 'New API task',
            'description': 'Created through API',
            'status': Task.TaskStatus.IN_PROGRESS,
            'priority': 4,
            'due_date': str(timezone.localdate() + timedelta(days=5)),
        }

        response = self.client.post(self.list_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 2)
        self.assertEqual(response.data['title'], payload['title'])

    def test_create_task_validation_errors(self):
        payload = {
            'title': '',
            'status': 'invalid_status',
            'priority': 6,
            'due_date': str(timezone.localdate() - timedelta(days=1)),
        }

        response = self.client.post(self.list_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)
        self.assertIn('status', response.data)
        self.assertIn('priority', response.data)
        self.assertIn('due_date', response.data)

    def test_get_task_list(self):
        Task.objects.create(
            title='Second task',
            status=Task.TaskStatus.DONE,
            priority=5,
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 2)

    def test_get_single_task(self):
        detail_url = reverse('task-detail', kwargs={'pk': self.task.id})

        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(self.task.id))

    def test_put_update_task(self):
        detail_url = reverse('task-detail', kwargs={'pk': self.task.id})
        payload = {
            'title': 'Updated with PUT',
            'description': 'Full update',
            'status': Task.TaskStatus.DONE,
            'priority': 5,
            'due_date': str(timezone.localdate() + timedelta(days=10)),
        }

        response = self.client.put(detail_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, payload['title'])
        self.assertEqual(self.task.status, payload['status'])
        self.assertEqual(self.task.priority, payload['priority'])

    def test_patch_update_task(self):
        detail_url = reverse('task-detail', kwargs={'pk': self.task.id})

        response = self.client.patch(
            detail_url,
            {'status': Task.TaskStatus.DONE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.TaskStatus.DONE)

    def test_delete_task(self):
        detail_url = reverse('task-detail', kwargs={'pk': self.task.id})

        response = self.client.delete(detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Task.objects.filter(id=self.task.id).exists())

    def test_404_for_nonexistent_id(self):
        detail_url = reverse('task-detail', kwargs={'pk': uuid.uuid4()})

        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_by_status_and_priority(self):
        Task.objects.create(
            title='Done task',
            status=Task.TaskStatus.DONE,
            priority=5,
        )
        Task.objects.create(
            title='In progress task',
            status=Task.TaskStatus.IN_PROGRESS,
            priority=2,
        )

        response = self.client.get(
            self.list_url,
            {'status': Task.TaskStatus.DONE, 'priority': 5},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Done task')

    def test_ordering_by_priority_desc(self):
        Task.objects.create(
            title='Low priority',
            status=Task.TaskStatus.TODO,
            priority=1,
        )
        Task.objects.create(
            title='High priority',
            status=Task.TaskStatus.TODO,
            priority=5,
        )

        response = self.client.get(self.list_url, {'ordering': '-priority'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        priorities = [item['priority'] for item in response.data['results']]
        self.assertEqual(priorities, sorted(priorities, reverse=True))

    def test_pagination(self):
        for index in range(11):
            Task.objects.create(
                title=f'Paginated task {index}',
                status=Task.TaskStatus.TODO,
                priority=1,
            )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 12)
        self.assertEqual(len(response.data['results']), 10)
        self.assertIsNotNone(response.data['next'])
