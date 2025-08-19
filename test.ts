// 禁用SSL证书验证（仅用于测试环境）
process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";

import OpenAI from "openai";
import { fetch as nodeFetch, ProxyAgent } from "undici";

function getFetch(url: RequestInfo | URL, opts?: RequestInit) {
  const urlString = url instanceof Request ? url.url : url.toString();
  // 将 RequestInit 转换为 undici 的 RequestInit 类型
  const undiciOpts = {
    ...opts,
    // dispatcher: new ProxyAgent("http://168.64.5.83:8080/"),
    // 在fetch级别也禁用SSL验证
    // @ts-ignore - 忽略 undici 和标准 fetch 之间的类型差异
    // rejectUnauthorized: false,
  };
  return nodeFetch(
    urlString,
    undiciOpts as any
  ) as unknown as Promise<Response>;
}

// const baseURL = "https://llm-proxy-605029883265.us-central1.run.app";
const baseURL = "http://ai-coding-v2.sit.saas.htsc";
// const baseURL = "http://localhost:8080";
// 配置OpenAI客户端指向本地代理服务
const openai = new OpenAI({
  // baseURL: "http://localhost:8080/v1",
  baseURL: `${baseURL}/v1`,
  apiKey: "not-needed", // 本地代理不需要API Key
  // 添加额外的fetch选项来处理SSL问题
  // fetch: getFetch,
});

async function testHealth() {
  console.log("🔍 测试健康检查接口...");
  try {
    const response = await getFetch(`${baseURL}/health`, {});
    if (response.ok) {
      const data = await response.json();
      console.log(`状态码: ${response.status}`);
      console.log(`响应: ${JSON.stringify(data)}`);
      return true;
    } else {
      console.log(`❌ 健康检查失败: ${response.status}`);
      return false;
    }
  } catch (error) {
    console.error(`❌ 健康检查失败: ${error}`);
    return false;
  }
}

async function testChatNonStream() {
  console.log("\n💬 测试非流式聊天接口 (OpenAI兼容模式)...");
  try {
    const chatCompletion = await openai.chat.completions.create({
      model: "gemini-2.5-pro", // 这个模型名称需要和服务器端匹配
      messages: [
        { role: "system", content: "你是一个乐于助人的助手。" },
        { role: "user", content: "你好，请用一句话介绍一下Google Gemini" },
      ],
      temperature: 0.7,
    });

    console.log(`状态码: 200`);
    console.log(`完整响应: ${JSON.stringify(chatCompletion, null, 2)}`);
    console.log(`助手回答: ${chatCompletion.choices[0].message.content}`);
    return true;
  } catch (error) {
    console.error("❌ 非流式聊天测试失败:", error);
    return false;
  }
}

async function testChatStream() {
  console.log("\n🌊 测试流式聊天接口 (OpenAI兼容模式)...");
  try {
    const stream = await openai.chat.completions.create({
      model: "gemini-2.5-pro",
      messages: [
        { role: "user", content: "请写一个简单的Python函数来计算斐波那契数列" },
      ],
      stream: true,
    });

    console.log(`状态码: 200`);
    console.log("流式响应:");
    let fullContent = "";
    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content || "";
      fullContent += content;
      process.stdout.write(content); // 逐块打印内容
    }
    console.log("\n✅ 流式响应完成");
    if (!fullContent) {
      console.log("\n⚠️ 流式响应为空");
    }
    return true;
  } catch (error) {
    console.error("❌ 流式聊天测试失败:", error);
    return false;
  }
}

async function testMultimodal() {
  console.log("\n🖼️ 测试多模态接口 (OpenAI兼容模式)...");
  try {
    const chatCompletion = await openai.chat.completions.create({
      model: "gemini-2.5-pro",
      messages: [
        {
          role: "user",
          content: [
            { type: "text", text: "请描述这张图片中的内容，用中文回答。" },
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

    console.log(`状态码: 200`);
    console.log(`完整响应: ${JSON.stringify(chatCompletion, null, 2)}`);
    console.log(`助手回答: ${chatCompletion.choices[0].message.content}`);
    return true;
  } catch (error) {
    console.error("❌ 多模态测试失败:", error);
    return false;
  }
}

async function main() {
  console.log("🚀 开始测试Gemini Vertex AI代理API...");
  console.log("📍 目标地址: ", baseURL);
  console.log("=".repeat(50));

  // 确保服务已启动
  if (!(await testHealth())) {
    console.log(
      "\n❌ 服务健康检查失败，无法继续测试。请确保app_vertex.py正在运行。"
    );
    return;
  }

  const tests = [
    { name: "非流式聊天", func: testChatNonStream },
    { name: "流式聊天", func: testChatStream },
    { name: "多模态", func: testMultimodal },
  ];

  const results: Array<{ name: string; success: boolean }> = [];
  for (const test of tests) {
    try {
      const success = await test.func();
      results.push({ name: test.name, success });
      await new Promise((resolve) => setTimeout(resolve, 1000)); // 等待1秒
    } catch (error) {
      console.error(`❌ ${test.name}测试出现意外异常: ${error}`);
      results.push({ name: test.name, success: false });
    }
  }

  console.log("\n" + "=".repeat(50));
  console.log("📊 测试结果汇总:");
  const passedTests: string[] = [];
  const failedTests: string[] = [];
  for (const result of results) {
    const status = result.success ? "✅ 通过" : "❌ 失败";
    console.log(`   ${result.name}: ${status}`);
    if (result.success) {
      passedTests.push(result.name);
    } else {
      failedTests.push(result.name);
    }
  }

  const passed = passedTests.length;
  const total = results.length;
  console.log(`\n🎯 总体结果: ${passed}/${total} 测试通过`);
  if (failedTests.length > 0) {
    console.log(`   失败的测试: ${failedTests.join(", ")}`);
  }
}

main();
