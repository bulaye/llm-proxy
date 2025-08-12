import OpenAI from "openai";

// 配置OpenAI客户端指向本地代理服务
const openai = new OpenAI({
  baseURL: "http://localhost:8080/v1",
  apiKey: "not-needed", // 本地代理不需要API Key
});

async function testChatCompletions() {
  console.log("--- Running Non-Streaming Test ---");
  try {
    const chatCompletion = await openai.chat.completions.create({
      model: "gemini-2.5-pro", // 这个模型名称需要和服务器端匹配
      messages: [
        { role: "system", content: "You are a helpful assistant." },
        { role: "user", content: "Hello! Can you tell me a joke?" },
      ],
      temperature: 0.7,
      max_tokens: 150,
    });

    console.log("Non-Streaming Response:");
    console.log(JSON.stringify(chatCompletion, null, 2));
    console.log("Assistant says:", chatCompletion.choices[0].message.content);
  } catch (error) {
    console.error("Non-Streaming Test Failed:", error);
  }

  console.log("\n--- Running Streaming Test ---");
  try {
    const stream = await openai.chat.completions.create({
      model: "gemini-2.5-pro",
      messages: [
        { role: "system", content: "You are a poetic assistant." },
        { role: "user", content: "Write a short poem about the moon." },
      ],
      stream: true,
    });

    console.log("Streaming Response:");
    let fullContent = "";
    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content || "";
      fullContent += content;
      process.stdout.write(content); // 逐块打印内容
    }
    console.log("\n\nFull streamed content:", fullContent);
  } catch (error) {
    console.error("Streaming Test Failed:", error);
  }
}

async function testMultimodalCompletions() {
  console.log("\n--- Running Multimodal Test ---");
  try {
    const chatCompletion = await openai.chat.completions.create({
      model: "gemini-2.5-pro",
      messages: [
        {
          role: "user",
          content: [
            { type: "text", text: "What’s in this image?" },
            {
              type: "image_url",
              image_url: {
                url: "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/1280px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
              },
            },
          ],
        },
      ],
      max_tokens: 300,
    });
    console.log("Multimodal Response:");
    console.log(JSON.stringify(chatCompletion, null, 2));
    console.log("Assistant says:", chatCompletion.choices[0].message.content);
  } catch (error) {
    console.error("Multimodal Test Failed:", error);
  }
}

async function main() {
  await testChatCompletions();
  await testMultimodalCompletions();
}

main();
