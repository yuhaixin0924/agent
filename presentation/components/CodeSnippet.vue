<script setup>
import { ref, watch } from 'vue'
import { createHighlighterCore } from 'shiki/core'
import { createJavaScriptRegexEngine } from 'shiki/engine/javascript'
import javascript from '@shikijs/langs/javascript'
import python from '@shikijs/langs/python'
import githubDark from '@shikijs/themes/github-dark'

const highlighter = createHighlighterCore({
  themes: [githubDark],
  langs: [javascript, python],
  engine: createJavaScriptRegexEngine(),
})

const props = defineProps({
  code: { type: String, required: true },
  language: { type: String, default: 'python' },
})
const highlighted = ref('')
let request = 0

watch(() => [props.code, props.language], async ([code, language]) => {
  const current = ++request
  highlighted.value = ''
  try {
    // 内容来自演示稿中的固定片段；Shiki 对代码进行转义并生成带颜色的标记。
    const html = (await highlighter).codeToHtml(code, { lang: language, theme: 'github-dark' })
    if (current === request) highlighted.value = html
  } catch {
    // 高亮加载失败时仍展示原始代码，避免讲解内容丢失。
    if (current === request) highlighted.value = ''
  }
}, { immediate: true })
</script>

<template>
  <div class="code-snippet">
    <div v-if="highlighted" class="highlighted" v-html="highlighted" />
    <pre v-else><code>{{ code }}</code></pre>
  </div>
</template>

<style scoped>
.code-snippet { min-width: 0; }
.code-snippet :deep(pre) { margin: 0; min-height: 123px; max-height: 145px; padding: 10px 12px; overflow: auto; border-radius: 6px; background: #0b1723 !important; color: #d5eee6; font: 12px/1.5 Consolas, monospace; white-space: pre-wrap; overflow-wrap: anywhere; }
.code-snippet :deep(code) { font: inherit; }
</style>
