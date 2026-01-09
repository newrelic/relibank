import { useState, useRef, useEffect } from 'react';
import { Box, Typography, Paper, TextField, Button, CircularProgress } from '@mui/material';
import SendIcon from '@mui/icons-material/Send'; 

// Define a type for a chat message for clarity, even if it's a JS file for now
interface ChatMessage {
  id: number;
  text: string;
  sender: 'user' | 'bot';
  timestamp: string;
}

const initialMessages: ChatMessage[] = [
  {
    id: 1,
    text: "Hello! I'm ReliBot, your virtual support agent. How can I help you today?",
    sender: 'bot',
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  },
];

export default function SupportPage() {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [inputMessage, setInputMessage] = useState('');
  const [isBotTyping, setIsBotTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the bottom when messages update
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages, isBotTyping]);

  // Demo scenario: Blocking synchronous Fibonacci calculation
  const calculateFibonacci = (n: number): number => {
    if (n <= 1) return n;
    return calculateFibonacci(n - 1) + calculateFibonacci(n - 2);
  };

  const handleSend = async () => {
    if (!inputMessage.trim()) return;

    const userMessageText = inputMessage.trim();

    // Demo scenario
    // Check for spending analysis triggers
    // This will match variations like:
    // - "analyze my spending"
    // - "Analyze my spending."
    // - "analyse my spending"
    // - "spending analysis"
    // - "check my spending"
    const spendingAnalysisTriggers = [
      /analyz[e]?\s+my\s+spending/i,
      /analys[e]?\s+spending/i,
      /spending\s+analys[ie]s/i,
      /check\s+my\s+spending/i
    ];

    const isSpendingAnalysis = spendingAnalysisTriggers.some(
      pattern => pattern.test(userMessageText)
    );

    if (isSpendingAnalysis) {
      // Demo scenario: Simulates heavy computation on main thread
      // This blocks the UI from updating before the user sees their message
      console.warn('[DEMO] Running blocking Fibonacci calculation for spending analysis...');
      const startTime = performance.now();
      const result = calculateFibonacci(42); // ~3-5 seconds on average CPU
      const endTime = performance.now();
      console.warn(`[DEMO] Blocking calculation complete: fib(42) = ${result}, took ${(endTime - startTime).toFixed(0)}ms`);
    }
    const newUserMessage: ChatMessage = {
      id: Date.now(),
      text: userMessageText,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    // 1. Add user message and clear input
    setMessages((prev: ChatMessage[]) => [...prev, newUserMessage]);
    setInputMessage('');
    setIsBotTyping(true);

    // 2. Make API Call to the chatbot service
    try {
      const apiUrl = `/chatbot-service/chat?prompt=${encodeURIComponent(userMessageText)}`;
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        // The chatbot service requires the prompt as a query parameter and the request method is POST.
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Chatbot service returned status ${response.status}`);
      }

      const data = await response.json();
      const botResponseText = data.response || "I received a response, but it was empty."; // Assuming response format is { response: "..." }

      // 3. Add bot response
      const newBotMessage: ChatMessage = {
        id: Date.now() + 1,
        text: botResponseText,
        sender: 'bot',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev: ChatMessage[]) => [...prev, newBotMessage]);

    } catch (error: unknown) {
      console.error("Chatbot API call failed:", error);
      const errorMessage: ChatMessage = {
        id: Date.now() + 1,
        text: `Sorry, I couldn't connect to the support service. Please ensure the chatbot service is running. Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        sender: 'bot',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev: ChatMessage[]) => [...prev, errorMessage]);
    } finally {
      setIsBotTyping(false);
    }
  };
  
  const handleKeyPress = (e: any) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const MessageBubble = ({ message }: { message: ChatMessage }) => {
    const isUser = message.sender === 'user';
    
    return (
      <Box sx={{ 
        alignSelf: isUser ? 'flex-end' : 'flex-start',
        maxWidth: '80%',
        mb: 1
      }}>
        <Paper 
          variant="outlined" 
          sx={{ 
            p: 1.5, 
            borderRadius: '12px', 
            // Customize border radius for chat bubbles
            borderBottomRightRadius: isUser ? 0 : 12,
            borderBottomLeftRadius: isUser ? 12 : 0,
            bgcolor: isUser ? 'primary.main' : 'white',
            color: isUser ? 'white' : 'text.primary',
            borderColor: '#e5e7eb',
            // Remove border for user messages since background is solid
            border: isUser ? 'none' : '1px solid #e5e7eb',
            boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
          }}
        >
          <Typography variant="body1">
            {message.text}
          </Typography>
        </Paper>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5, ml: isUser ? 'auto' : 1, mr: isUser ? 1 : 'auto', textAlign: isUser ? 'right' : 'left' }}>
          {message.timestamp}
        </Typography>
      </Box>
    );
  };

  return (
    <Box sx={{ px: 48, py: 3, display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Customer Support Chat
      </Typography>
      
      {/* Chat Window Container */}
      <Paper 
        elevation={3} 
        sx={{ 
          flexGrow: 1, 
          display: 'flex', 
          flexDirection: 'column', 
          borderRadius: '12px', 
          overflow: 'hidden',
          minHeight: '400px', // Ensure minimum size
          bgcolor: '#f3f4f6', 
        }}
      >
        {/* Messages Display Area */}
        <Box 
          sx={{ 
            flexGrow: 1, 
            p: 2, 
            overflowY: 'auto', 
            display: 'flex', 
            flexDirection: 'column'
          }}
        >
          {messages.map((message: ChatMessage) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          
          {/* Typing Indicator */}
          {isBotTyping && (
            <Box sx={{ alignSelf: 'flex-start', maxWidth: '70%', mb: 1 }}>
              <Paper variant="outlined" sx={{ p: 1.5, borderRadius: '12px', borderBottomLeftRadius: 0, bgcolor: 'white', borderColor: '#e5e7eb' }}>
                <CircularProgress size={12} sx={{ mr: 1 }} />
                <Typography variant="body2" component="span">
                  ReliBot is waiting for a response...
                </Typography>
              </Paper>
            </Box>
          )}

          {/* Invisible anchor for scrolling */}
          <div ref={messagesEndRef} />
        </Box>

        {/* Input Area */}
        <Box sx={{ p: 2, borderTop: '1px solid #e5e7eb', bgcolor: 'white', display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            variant="outlined"
            placeholder="Type your message (Press Enter to send)..."
            autoFocus 
            size="small"
            value={inputMessage}
            onChange={(e: any) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isBotTyping}
          />
          <Button 
            variant="contained" 
            color="primary" 
            endIcon={<SendIcon />}
            onClick={handleSend} 
            disabled={!inputMessage.trim() || isBotTyping}
            sx={{ flexShrink: 0 }}
          >
            Send
          </Button>
        </Box>
      </Paper>
    </Box>
  );
}
