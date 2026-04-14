import type { SpendingCategoriesProps } from './types';

const SpendingCategories = ({ data }: SpendingCategoriesProps) => {
  const { Card, Box, Typography } = window.MaterialUI;
  const { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } = window.Recharts;

  return (
    <Card sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Typography variant="h6" sx={{ mb: 2 }}>Spending over last 6 months</Typography>
      <Box sx={{ height: 300 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              labelLine={false}
              outerRadius={100}
              dataKey="value"
              label={({ name, percent }: { name: string; percent: number }) => `${name} ${(percent * 100).toFixed(0)}%`}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </Box>
    </Card>
  );
};

export default SpendingCategories;
