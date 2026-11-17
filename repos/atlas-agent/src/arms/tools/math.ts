/**
 * Atlas Math Tool - Safe mathematical calculations
 */

import { logger } from '../../common/logger.js';

const SAFE_MATH_FNS: Record<string, any> = {
  abs: Math.abs,
  ceil: Math.ceil,
  floor: Math.floor,
  round: Math.round,
  sqrt: Math.sqrt,
  pow: Math.pow,
  min: Math.min,
  max: Math.max,
  log: Math.log,
  log2: Math.log2,
  log10: Math.log10,
  sin: Math.sin,
  cos: Math.cos,
  tan: Math.tan,
  exp: Math.exp,
  PI: Math.PI,
  E: Math.E,
};

export class MathTool {
  private static instance: MathTool;

  private constructor() {}

  static getInstance(): MathTool {
    if (!MathTool.instance) {
      MathTool.instance = new MathTool();
    }
    return MathTool.instance;
  }

  calculate(expression: string): string {
    try {
      // 0. Frases en lenguaje humano que traían frases sueltas (el modelo
      //    bash a veces pasa "raíz cuadrada de 196" en vez de sqrt(196)).
      let expr = expression
        .replace(/ra[íi]z\s+cuadrada\s+de\s*([0-9.,]+)\b/gi, 'sqrt($1)')
        .replace(/ra[íi]z\s+de\s*([0-9.,]+)\b/gi, 'sqrt($1)')
        // porcentaje: "15% de 2350" → (15/100)*2350 (el % como operador de
        // modulo daba "15" con el 2350 después).
        .replace(/(\d+(?:[.,]\d+)?)\s*%\s*de\s*([0-9.,]+)/gi, '($1/100)*$2')

      // 1. Notación común ANTES de sanitizar (si no, el sanitize borraba ×, ÷, π
      //    y esos reemplazos eran código muerto). 'x' junto a dígitos es
      //    multiplicación ("2 x 3", "2x3"), sin tocar nombres de funciones.
        .replace(/(\d)\s*[xX×·]\s*(?=[\d(])/g, '$1*')
        .replace(/×|·/g, '*')
        .replace(/÷/g, '/')
        .replace(/\^/g, '**')
        .replace(/π|\bpi\b/gi, String(Math.PI));

      // 2. Sanitize: solo números, operadores, paréntesis, espacios, puntos,
      //    comas Y LETRAS que formen funciones/constantes seguras. El viejo
      //    sanitize borraba TODAS las letras ANTES de reemplazar sqrt/log/etc
      //    → "sqrt(196)" evaluaba "(196)" = 196.
      expr = expr.replace(/[^0-9+\-*/().%\sa-zA-Z,]/g, '');
      expr = expr.replace(/\b[a-zA-Z_][a-zA-Z0-9_]*\b/g, (token) => {
        if (Object.prototype.hasOwnProperty.call(SAFE_MATH_FNS, token)) return token;
        if (token === 'e') return token;
        return '';
      });

      // 3. Comas: si hay funciones (letras), separan argumentos; si no hay,
      //    son decimales en notación española ("2,5" → 2.5). Antes TODAS las
      //    comas se convertían a puntos y min(2,3) → min(2.3) fallaba.
      if (!/[a-zA-Z]/.test(expr)) {
        expr = expr.replace(/,/g, '.');
      }

      // 4. Euler 'e' suelto (después del sanitize, que conserva letras)
      expr = expr.replace(/(?<=^|[\s+\-*/(,.])e(?=[\s+\-*^/),.]|$)/gi, String(Math.E));

      // 5. Nombres de funciones
      for (const fn of Object.keys(SAFE_MATH_FNS)) {
        const regex = new RegExp(`\\b${fn}\\b`, 'gi');
        expr = expr.replace(regex, `SAFE_MATH_FNS.${fn}`);
      }

      // Evaluate in sandboxed context
      const fn = new Function('SAFE_MATH_FNS', `"use strict"; return (${expr});`);
      const result = fn(SAFE_MATH_FNS);

      if (typeof result !== 'number' || !isFinite(result)) {
        return `Resultado: ${result} (posiblemente indefinido)`;
      }

      logger.info('math', `Calculated: "${expression}" = ${result}`);
      return `Resultado: ${result}`;
    } catch (err: any) {
      logger.error('math', `Calculation failed: ${err.message}`);
      return `Error calculando "${expression}": ${err.message}. Usá notación matemática estándar (ej: 2+3*4, sqrt(16), 2**10).`;
    }
  }
}

export const mathTool = MathTool.getInstance();
