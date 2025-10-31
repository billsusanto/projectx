import createClient from 'openapi-fetch';
import type { paths, components } from '@/types/types';

export const apiClient = createClient<paths>({
  baseUrl: 'http://localhost:8000',
});

export async function createTodo(todo: components['schemas']['TodoCreate']) {
  return apiClient.POST('/todos/', { body: todo });
}

export async function getTodos() {
  return apiClient.GET('/todos/');
}

export async function updateTodo(id: number, todo: components['schemas']['TodoUpdate']) {
  return apiClient.PUT('/todos/{id}', { params: { path: { id } }, body: todo });
}

export async function deleteTodo(id: number) {
  return apiClient.DELETE('/todos/{id}', { params: { path: { id } } });
}