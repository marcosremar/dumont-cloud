require('dotenv').config({ path: '../.env' });

console.log('OPENROUTER_API_KEY:', process.env.OPENROUTER_API_KEY);
console.log('API Key length:', process.env.OPENROUTER_API_KEY?.length);
console.log('API Key starts with:', process.env.OPENROUTER_API_KEY?.substring(0, 15));
