
import { QueryClient, QueryClientProvider } from 'react-query';
import AganithaLoginInner from './AganithaLoginInner';

// Create a client
const queryClient = new QueryClient();

export default function AganithaLogin() {
    return (
        <QueryClientProvider client={queryClient}>
            
            <AganithaLoginInner />
        </QueryClientProvider>
    );
}
