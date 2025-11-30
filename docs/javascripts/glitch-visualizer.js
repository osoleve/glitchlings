/**
 * Glitchlings Visualizer - Interactive Before/After Text Corruption Demo
 * 
 * A lightweight JavaScript visualizer for demonstrating glitchling effects
 * in real-time within the documentation.
 */

(function() {
    'use strict';

    // Sample corruption algorithms (client-side approximations)
    const corruptors = {
        typogre: {
            name: 'Typogre',
            description: 'Keyboard-adjacent typos',
            corrupt: function(text, rate, seed) {
                const neighbors = {
                    'a': 'sqwz', 'b': 'vghn', 'c': 'xdfv', 'd': 'serfcx',
                    'e': 'wsdfr', 'f': 'dcvgrt', 'g': 'fvbhty', 'h': 'gbnjuy',
                    'i': 'ujklo', 'j': 'hnmkui', 'k': 'jmlio', 'l': 'kop',
                    'm': 'njk', 'n': 'bhjm', 'o': 'iklp', 'p': 'ol',
                    'q': 'wa', 'r': 'edft', 's': 'awedxz', 't': 'rfgy',
                    'u': 'yhji', 'v': 'cfgb', 'w': 'qase', 'x': 'zsdc',
                    'y': 'tghu', 'z': 'asx'
                };
                const rng = seededRandom(seed);
                return text.split('').map(char => {
                    const lower = char.toLowerCase();
                    if (neighbors[lower] && rng() < rate) {
                        const opts = neighbors[lower];
                        const replacement = opts[Math.floor(rng() * opts.length)];
                        return char === lower ? replacement : replacement.toUpperCase();
                    }
                    return char;
                }).join('');
            }
        },
        mim1c: {
            name: 'Mim1c',
            description: 'Homoglyph substitution',
            corrupt: function(text, rate, seed) {
                const homoglyphs = {
                    'a': 'αа', 'e': 'еҽ', 'o': 'οо', 'c': 'ϲс',
                    'p': 'рρ', 'x': 'хχ', 'y': 'уγ', 'i': 'іι',
                    'A': 'ΑА', 'E': 'ЕΕ', 'O': 'ОΟ', 'C': 'СϹ',
                    'H': 'НΗ', 'M': 'МΜ', 'T': 'ТΤ', 'B': 'ВΒ'
                };
                const rng = seededRandom(seed);
                return text.split('').map(char => {
                    if (homoglyphs[char] && rng() < rate) {
                        const opts = homoglyphs[char];
                        return opts[Math.floor(rng() * opts.length)];
                    }
                    return char;
                }).join('');
            }
        },
        redactyl: {
            name: 'Redactyl',
            description: 'Word redaction',
            corrupt: function(text, rate, seed) {
                const rng = seededRandom(seed);
                return text.split(/(\s+)/).map(token => {
                    if (token.trim() && rng() < rate) {
                        return '█'.repeat(token.length);
                    }
                    return token;
                }).join('');
            }
        },
        scannequin: {
            name: 'Scannequin',
            description: 'OCR artifacts',
            corrupt: function(text, rate, seed) {
                const confusions = {
                    'rn': 'm', 'm': 'rn', 'cl': 'd', 'd': 'cl',
                    'l': '1', '1': 'l', 'O': '0', '0': 'O',
                    'vv': 'w', 'w': 'vv', 'I': 'l', 'h': 'li'
                };
                const rng = seededRandom(seed);
                let result = text;
                for (const [from, to] of Object.entries(confusions)) {
                    if (rng() < rate * 2) {
                        result = result.replace(new RegExp(from, 'g'), (match) => {
                            return rng() < rate ? to : match;
                        });
                    }
                }
                return result;
            }
        },
        hokey: {
            name: 'Hokey',
            description: 'Character stretching',
            corrupt: function(text, rate, seed) {
                const stretchable = 'aeiouAEIOU';
                const rng = seededRandom(seed);
                return text.split('').map(char => {
                    if (stretchable.includes(char) && rng() < rate) {
                        const repeats = 2 + Math.floor(rng() * 4);
                        return char.repeat(repeats);
                    }
                    return char;
                }).join('');
            }
        },
        zeedub: {
            name: 'Zeedub',
            description: 'Zero-width injection',
            corrupt: function(text, rate, seed) {
                const zwChars = ['\u200B', '\u200C', '\u200D', '\uFEFF'];
                const rng = seededRandom(seed);
                return text.split('').map(char => {
                    if (char.trim() && rng() < rate) {
                        const zw = zwChars[Math.floor(rng() * zwChars.length)];
                        return char + zw;
                    }
                    return char;
                }).join('');
            }
        },
        rushmore: {
            name: 'Rushmore',
            description: 'Word deletion',
            corrupt: function(text, rate, seed) {
                const rng = seededRandom(seed);
                return text.split(/(\s+)/).filter(token => {
                    if (token.trim()) {
                        return rng() >= rate;
                    }
                    return true;
                }).join('');
            }
        }
    };

    // Seeded random number generator
    function seededRandom(seed) {
        let s = seed || 42;
        return function() {
            s = (s * 1103515245 + 12345) & 0x7fffffff;
            return s / 0x7fffffff;
        };
    }

    // Diff highlighting
    function highlightDiff(original, corrupted) {
        const result = [];
        let i = 0, j = 0;
        
        while (i < original.length || j < corrupted.length) {
            if (i < original.length && j < corrupted.length && original[i] === corrupted[j]) {
                result.push(document.createTextNode(corrupted[j]));
                i++; j++;
            } else if (j < corrupted.length) {
                const span = document.createElement('span');
                span.className = 'glitch-diff-add';
                span.textContent = corrupted[j];
                result.push(span);
                j++;
                if (i < original.length && original[i] !== corrupted[j]) {
                    i++;
                }
            } else {
                i++;
            }
        }
        
        return result;
    }

    // Initialize visualizer
    function initVisualizer(container) {
        const glitchlingSelect = container.querySelector('.glitch-select');
        const rateSlider = container.querySelector('.glitch-rate');
        const rateValue = container.querySelector('.glitch-rate-value');
        const seedInput = container.querySelector('.glitch-seed');
        const inputText = container.querySelector('.glitch-input');
        const outputBefore = container.querySelector('.glitch-before');
        const outputAfter = container.querySelector('.glitch-after');

        function update() {
            const glitchling = glitchlingSelect.value;
            const rate = parseFloat(rateSlider.value);
            const seed = parseInt(seedInput.value) || 42;
            const text = inputText.value;

            rateValue.textContent = (rate * 100).toFixed(0) + '%';

            if (corruptors[glitchling]) {
                const corrupted = corruptors[glitchling].corrupt(text, rate, seed);
                outputBefore.textContent = text;
                
                // Clear and add highlighted diff
                outputAfter.innerHTML = '';
                const diffNodes = highlightDiff(text, corrupted);
                diffNodes.forEach(node => outputAfter.appendChild(node));
            }
        }

        glitchlingSelect.addEventListener('change', update);
        rateSlider.addEventListener('input', update);
        seedInput.addEventListener('input', update);
        inputText.addEventListener('input', update);

        // Initial render
        update();
    }

    // Auto-initialize all visualizers on page load
    function init() {
        document.querySelectorAll('.glitch-visualizer').forEach(initVisualizer);
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose for manual initialization
    window.GlitchVisualizer = {
        init: init,
        initContainer: initVisualizer,
        corruptors: corruptors
    };
})();
