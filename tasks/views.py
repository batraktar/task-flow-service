from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from tasks.models import Task
from tasks.serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_fields = ('status', 'priority')
    ordering_fields = ('created_at', 'due_date', 'priority')
    ordering = ('-created_at',)
