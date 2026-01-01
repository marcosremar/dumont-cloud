/**
 * Test Z.ai API to check available models
 */

const https = require('https');

const apiKey = 'dbad137a37ca4618b03174ecf186a192.pI1JegJItU855rRa';
const models = ['glm-4v', 'glm-4', 'glm-4-plus', 'glm-4-air'];

async function testModel(model) {
  return new Promise((resolve) => {
    const data = JSON.stringify({
      model: model,
      messages: [{
        role: 'user',
        content: 'Hello'
      }]
    });

    const options = {
      hostname: 'open.bigmodel.cn',
      port: 443,
      path: '/api/paas/v4/chat/completions',
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'Content-Length': data.length
      }
    };

    const req = https.request(options, (res) => {
      let responseData = '';

      res.on('data', (chunk) => {
        responseData += chunk;
      });

      res.on('end', () => {
        console.log(`\n=== Testing model: ${model} ===`);
        console.log(`Status: ${res.statusCode}`);
        if (res.statusCode === 200) {
          console.log('✅ Model WORKS!');
          const parsed = JSON.parse(responseData);
          console.log('Response:', JSON.stringify(parsed, null, 2));
        } else {
          console.log('❌ Model FAILED');
          console.log('Response:', responseData);
        }
        resolve();
      });
    });

    req.on('error', (error) => {
      console.error(`\n=== Testing model: ${model} ===`);
      console.error('❌ Error:', error.message);
      resolve();
    });

    req.write(data);
    req.end();
  });
}

async function main() {
  console.log('Testing Z.ai API models...\n');
  for (const model of models) {
    await testModel(model);
    // Wait a bit between requests
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
}

main();
