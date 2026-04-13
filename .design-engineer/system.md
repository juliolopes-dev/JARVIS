# Jarvis — Design System

## Direção: Dark · Technical & Precise

**Personalidade:** HUD do Homem de Ferro — sofisticado, funcional, imediato. Dark mode como padrão absoluto. Zero gradientes decorativos. Cada pixel justificado.

**Usuário:** Julio, único. App pessoal de uso intenso diário.

**Emotional job:** Controle, confiança, velocidade. O Jarvis sabe de tudo — a UI reflete isso.

---

## Tokens

### Cores
```
Surface base:    #09090b  (zinc-950)   → bg do app
Surface raised:  #111113               → cards, painéis laterais
Surface overlay: #18181b  (zinc-900)   → popovers, hover states
Border:          #27272a  (zinc-800)   → divisores, contornos
Muted:           #3f3f46  (zinc-700)   → desabilitado, inativo

Accent:          #3b82f6  (blue-500)   → ação primária, links, foco
Accent hover:    #2563eb  (blue-600)
Accent faint:    #1e3a5f               → bg de badges, highlights
Accent glow:     rgba(59,130,246,0.15) → ring de foco, seleção

Text primary:    #fafafa  (zinc-50)    → títulos, conteúdo principal
Text secondary:  #a1a1aa  (zinc-400)   → rótulos, metadados
Text muted:      #71717a  (zinc-500)   → placeholders, timestamps
Text faint:      #52525b  (zinc-600)   → divisores com texto

Status success:  #22c55e  (green-500)
Status warning:  #f59e0b  (amber-500)
Status error:    #ef4444  (red-500)
Status info:     #3b82f6  (blue-500)   ← same as accent
```

### Tipografia
```
Font sans:  Inter (400, 500, 600)
Font mono:  JetBrains Mono (400, 500)

Scale:
  2xs: 11px/16px  — badges, timestamps compactos
  xs:  12px/16px  — metadados, labels
  sm:  13px/20px  — texto secundário, tooltips
  base: 14px/22px — corpo principal ← tamanho padrão
  md:  15px/24px  — texto de chat
  lg:  16px/24px  — títulos de seção
  xl:  18px/28px  — títulos de página
  2xl: 24px/32px  — headings grandes
  3xl: 32px/40px  — (reservado)

Pesos:
  400 → corpo de texto
  500 → labels, botões, itens de nav
  600 → títulos, headings
```

### Espaçamento (4px grid)
```
4px  → micro (gap entre ícone e texto)
8px  → tight (padding interno compacto)
12px → standard (padding de elementos)
16px → comfortable (padding de cards, seções)
24px → generous (separação entre blocos)
32px → major (separação de seções grandes)
48px → page padding horizontal (desktop)
```

### Border Radius
```
4px  → badges, tags compactas
6px  → botões, inputs (DEFAULT)
8px  → cards, painéis
10px → modais, popovers grandes
12px → (reservado para elementos maiores)
```

### Profundidade — Borders-only
Dark UI não usa sombras. Hierarquia via cor de superfície + borda sutil.
```
Border padrão:   1px solid #27272a   (zinc-800)
Border sutil:    1px solid rgba(255,255,255,0.06)
Border accent:   1px solid rgba(59,130,246,0.5)
Float (menus):   box-shadow: 0 4px 16px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.06)
```

---

## Padrões de Componentes

### Button Primary
```
Height: 36px
Padding: 0 16px
Radius: 6px
Font: 13px, 500
Bg: #3b82f6 → hover: #2563eb
Text: #fff
Transition: 150ms
cursor-pointer obrigatório
Estado loading: spinner inline, disabled
```

### Button Ghost
```
Height: 36px
Padding: 0 12px
Radius: 6px
Font: 13px, 500
Bg: transparent → hover: #18181b
Text: #a1a1aa → hover: #fafafa
Border: none
```

### Button Destructive
```
Igual ao Primary mas:
Bg: transparent → hover: rgba(239,68,68,0.1)
Text: #ef4444
Border: 1px solid rgba(239,68,68,0.3)
```

### Input / Textarea
```
Height: 36px (inputs), auto (textareas)
Padding: 0 12px / 10px 12px
Radius: 6px
Bg: #111113
Border: 1px solid #27272a → focus: 1px solid #3b82f6
Font: 14px, 400
Text: #fafafa
Placeholder: #52525b
Focus ring: box-shadow: 0 0 0 3px rgba(59,130,246,0.15)
Transition: 150ms
```

### Card
```
Bg: #111113
Border: 1px solid #27272a
Radius: 8px
Padding: 16px
Sem sombra — borda faz o trabalho
```

### Badge
```
Height: 20px
Padding: 0 6px
Radius: 4px
Font: 11px, 500
Variantes:
  default → bg: #18181b, text: #a1a1aa, border: #27272a
  accent  → bg: #1e3a5f, text: #3b82f6, border: rgba(59,130,246,0.3)
  success → bg: rgba(34,197,94,0.1), text: #22c55e, border: rgba(34,197,94,0.3)
  error   → bg: rgba(239,68,68,0.1), text: #ef4444, border: rgba(239,68,68,0.3)
```

### Sidebar
```
Width: 260px
Bg: #09090b (mesma do app — border separa)
Border-right: 1px solid #27272a
Nav item height: 32px
Nav item padding: 0 12px
Nav item radius: 6px
Nav item active: bg #18181b, text #fafafa
Nav item hover: bg rgba(255,255,255,0.04)
Nav item text: 13px, 500
```

### Message Bubble (Chat)
```
User:
  Alinhamento: direita
  Bg: #1e3a5f
  Border: 1px solid rgba(59,130,246,0.2)
  Radius: 10px 10px 4px 10px
  Padding: 12px 16px
  Font: 15px, 400