"use client";

import React, { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';
import type { components } from '@/types/types';

type Todo = components['schemas']['TodoRead'];

interface TodoItemProps {
  id: number;
}

const TodoItem = ({ id }: TodoItemProps) => {
  const [todo, setTodo] = useState<Todo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTodo = async () => {
      setLoading(true);
      setError(null);

      const { data, error } = await apiClient.GET('/todos/{id}', {
        params: {
          path: { id },
        },
      });

      if (error) {
        setError('Failed to fetch todo');
      } else {
        setTodo(data);
      }

      setLoading(false);
    };

    fetchTodo();
  }, [id]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!todo) return <div>Todo not found</div>;

  return (
    <div>
      <h3>{todo.title}</h3>
      <p>{todo.description}</p>
      <p>Completed: {todo.completed ? 'Yes' : 'No'}</p>
      <p>Priority: {todo.priority || 'None'}</p>
    </div>
  );
};

export default TodoItem;