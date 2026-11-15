# Every scientist a modeller? The promise and peril of AI-assisted mechanistic models

## Article Information

**Title:** Every scientist a modeller? The promise and peril of AI-assisted mechanistic models
**Authors:** Sen Gupta, Alex
**Year:** 2026
**Journal/Conference:** Methods in Ecology and Evolution
**Keywords:** ML/AI, Biological Impacts, Australia
**DOI:** 10.1111/2041-210x.70436  

---

## Quick Summary (100 words)

AI can help scientists build simulations without advanced maths or coding skills—but what happens when it also makes scientific decisions for them? This article argues that wider access to modelling brings both opportunities and risks. In a predator–prey example, an AI’s choice about how feeding rates change with prey abundance can determine whether populations stabilise or repeatedly boom and bust. The author recommends spelling out assumptions, asking AI to explain equations in everyday language, and testing simulations against expected outcomes. Used thoughtfully, AI could help researchers and students explore complex systems without giving up the critical thinking needed to understand them.

---

## Detailed Briefing (800-1000 words)

## 1. Background/Context

A scientist can understand an ecosystem without knowing how to build a computer simulation of it. An ecologist might know how predators affect prey, for example, but lack the mathematics and programming skills needed to turn that knowledge into a working model.

Generative artificial intelligence is changing that. Tools such as ChatGPT, Claude and Gemini can translate descriptions into equations, write code and build interactive simulations. Researchers, teachers and students can then adjust settings and watch a system respond.

In this 2026 Perspective article, Alex Sen Gupta of the University of New South Wales, Australia, explores the opportunity—and the danger—this creates. His central question is not simply whether AI can build models, but whether people can use those models responsibly without doing the technical work themselves.

The concern is that traditional model-building taught more than coding. It forced scientists to examine assumptions and make explicit decisions. AI can remove the technical obstacles while also removing those valuable moments of reflection.

## 2. Main Research/Argument

This is an argument supported by published research and worked examples, not a new experiment measuring AI’s effects on scientists. Sen Gupta follows four stages of model development: defining the system, translating that description into equations or rules, implementing it in code, and exploring the results.

His main example is a predator–prey system. Prey reproduce, predators eat them, consumption supports predator reproduction, and both populations experience mortality. An epidemic simulation provides a parallel example.

A mechanistic model is essentially a simplified working explanation: specify how the parts interact, then see what happens. Unlike a statistical association, it represents proposed processes. Think of the difference between noticing that traffic jams accompany rush hour and building a simulation of how cars, junctions and driving behaviour produce congestion.

AI can help at every stage, but it also makes choices. “Build me a predator–prey model” leaves important questions unanswered: Does food limit prey growth? Can predators consume unlimited prey? Does reproduction happen immediately after feeding?

Sen Gupta argues that these decisions must remain visible and subject to human judgement. AI should act as a translator and collaborator, not an unquestioned authority.

## 3. Key Findings

### Small assumptions can transform the outcome

The predator–prey example shows why apparently minor choices matter. If predation increases directly with prey density, doubling prey means each predator kills twice as many. There is no upper limit.

Alternatively, feeding can level off because catching, handling and digesting prey takes time. A third possibility is an S-shaped response, associated with behaviour such as switching between prey types.

These are established alternatives, described through Holling’s 1959 framework. In the article’s illustration, linear predation produces oscillations that fade towards a stable balance. Saturating predation can produce persistent boom-and-bust cycles under otherwise comparable conditions.

The lesson is that an AI-selected default can change the scientific story, not just the appearance of a graph.

### Better performance today can conceal weaker learning tomorrow

The article draws on evidence outside model-building, while acknowledging that limitation.

A 2025 study by Bastani and colleagues randomly allocated nearly **1,000 high-school students** to an unrestricted chatbot, a hint-giving AI tutor, or no AI. Both AI tools improved performance while available. But on a later examination without AI, students who had used the unrestricted chatbot scored **17% lower** than those without AI access. The hint-only tutor did not produce that decline.

A 2026 study involving **1,222 participants** also found poorer independent performance and reduced persistence after AI assistance. Another 2026 trial, involving software developers learning an unfamiliar library, found **17% lower scores** on conceptual understanding and debugging among AI-assisted participants. Those who sought explanations rather than simply delegating retained their learning.

These studies support a warning, rather than directly proving that AI-assisted modelling causes the same effects.

### Verification needs to be practical

Sen Gupta proposes checks that do not depend on advanced programming:

- **Write the conceptual model first.** Describe components, interactions and deliberate simplifications before requesting code.
- **Translate equations back into ordinary language.** Ask what each term assumes about the real system.
- **Test predictable situations.** For example, without prey reproduction, the illustrated system should eventually lose both populations.
- **Compare with published results.** Reproduce an established model’s behaviour using its reported parameters.
- **Build an interface that encourages questioning.** Display equations, parameter explanations, diagnostic checks and comparison scenarios.

The epidemic example makes this concrete: a researcher describes island communities connected by ferries, then asks Gemini to clarify assumptions before coding. Questions about recovery timing and commuting patterns expose decisions that might otherwise remain hidden.

## 4. Significance & Real-World Implications

The immediate benefit is wider access to mechanistic thinking. Someone who understands an ecosystem but cannot program could explore how interacting processes generate population changes. Teachers could let students investigate disease spread rather than merely memorise a diagram.

The island epidemic example illustrates the practical value: ferry connections and commuting rules can be varied to investigate how movement shapes transmission. Such exploration can help identify consequential assumptions, although it does not automatically produce a reliable public-health forecast.

The risks matter because convincing visuals can disguise incorrect models. A polished dashboard may inspire confidence even when its equations, code or numerical calculations are flawed.

Warning signs include negative populations, broken conservation balances, or results that change qualitatively when the simulation’s time step changes slightly. Unexpected behaviour should trigger investigation—not automatic acceptance or immediate dismissal.

## 5. Broader Takeaways

The article’s central paradox is that making modelling easier can either expand understanding or weaken it. The difference depends on what users delegate.

For someone who would otherwise never build a model, AI offers a genuine new opportunity. For someone who would otherwise learn the underlying methods, unrestricted delegation may sacrifice valuable skills.

Education therefore needs to assess the thinking around simulations: stating assumptions, explaining mechanisms, designing tests and interpreting unexpected results—not simply submitting working software.

These safeguards must also be repeated whenever a model changes. Faster rebuilding means more opportunities to experiment, but also more opportunities for unnoticed assumptions to enter.

Sen Gupta’s conclusion is cautiously optimistic: AI can make modelling accessible without making judgement optional. The goal is not to preserve technical difficulty for its own sake. It is to preserve the questioning that difficulty once forced people to do.

---

*Generated by PDF Summarizer using Gemini API*
*Source: Methods Ecol Evol - 2026 - Sen Gupta - Every scientist a modeller  The promise and peril of AI%E2%80%90assisted mechanistic models.pdf*
