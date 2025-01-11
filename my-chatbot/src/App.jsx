import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ChatInterface from './ChatGPTInterface'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="h-screen">
        <ChatInterface />
      </div>
    </QueryClientProvider>
  )
}

export default App