import type { AccountBalanceTrendsProps } from './types';

const AccountBalanceTrends = ({ data }: AccountBalanceTrendsProps) => {
  const { Card, Box, Typography } = window.MaterialUI;
  const { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } = window.Recharts;

  return (
    <Card sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Typography variant="h6" sx={{ mb: 2 }}>Account Balance Trends</Typography>
      <Box sx={{ height: 300 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="checking" stackId="a" fill="#1a3d1a" name="Checking" />
            <Bar dataKey="savings" stackId="a" fill="#7a9b3e" name="Savings" />
          </BarChart>
        </ResponsiveContainer>
      </Box>
    </Card>
  );
};

export default AccountBalanceTrends;
