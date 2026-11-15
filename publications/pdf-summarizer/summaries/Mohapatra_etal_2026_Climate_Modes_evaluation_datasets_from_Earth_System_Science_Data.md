# Climate Modes evaluation datasets from CMIP6 pre-industrial control simulations and observations

## Article Information

**Title:** Climate Modes evaluation datasets from CMIP6 pre-industrial control simulations and observations
**Authors:** Mohapatra, Sandeep; Sen Gupta, Alex; Bindoff, Nathaniel L.; Lyu, Yuxuan
**Year:** 2026
**Journal/Conference:** Earth System Science Data
**Keywords:** Climate variability, Climate models, Observation/Reanalysis, Model–observation synthesis, ENSO, Indian Ocean Dipole, Southern Annular Mode
**DOI:** 10.5194/essd-18-5463-2026  

---

## Quick Summary (100 words)

Recurring climate patterns like El Niño can amplify or mask long-term warming, but studying them requires processing huge amounts of data. This study provides ready-to-use datasets for eight major climate patterns from 23 climate models, each covering at least 500 simulated years, alongside observational records. The models broadly reproduce these patterns, especially atmospheric shifts such as the Southern Annular Mode. However, they struggle more with Central Pacific El Niño and Atlantic multidecadal temperature changes. The freely available data can help researchers separate natural variability from human-driven climate change, assess models, and strengthen the evidence used for climate planning and adaptation.

---

## Detailed Briefing (800-1000 words)

## 1. Background/Context

Climate change does not unfold as a smooth, steadily rising line. Alongside human-driven warming, the climate system has its own fluctuations: recurring patterns that influence ocean temperatures, atmospheric pressure, winds, and rainfall. These “climate modes” include El Niño and less familiar patterns such as the Indian Ocean Dipole and Southern Annular Mode.

Understanding these fluctuations matters because they can temporarily strengthen or mask the long-term warming trend. They also affect monsoons, ocean circulation, sea level, and ocean heat storage. Separating natural variability from human influence is therefore essential for interpreting climate records and assessing future risks.

Researchers face a practical obstacle, however: extracting these patterns from climate simulations requires handling enormous datasets. Calculating heat stored hundreds of metres below the ocean surface is especially demanding.

This study addresses that bottleneck by creating a publicly available collection of eight major climate modes from long climate-model simulations, alongside equivalent observational and reanalysis products. Its central contribution is a reusable research resource—not an investigation of a particular disaster or a forecast of the next El Niño.

## 2. Main Research/Argument

The researchers analysed **23 models from the Coupled Model Intercomparison Project Phase 6**, usually shortened to CMIP6. They selected pre-industrial control simulations lasting at least **500 years**, with the longest covering **2,000 years**.

These simulations keep external forcing approximately fixed at pre-industrial conditions. Think of them as a virtual laboratory where researchers can watch the climate fluctuate without adding the steadily increasing greenhouse gases of the industrial era.

The dataset covers:

- Eastern Pacific and Central Pacific El Niño;
- the Interdecadal Pacific Oscillation;
- the Indian Ocean Dipole;
- the Subsurface Dipole Mode;
- the Atlantic Multidecadal Oscillation;
- the North Atlantic Oscillation;
- the Southern Annular Mode.

For comparison, the team used sea-surface temperatures from **ERSSTv5 for 1900–2023**, ocean temperatures from **ORAS5 for 1958–2018**, and atmospheric pressure from **ERA5 for 1940–2023**. Reanalyses such as ORAS5 and ERA5 combine observations with numerical models to reconstruct past conditions.

The researchers put all datasets onto a common **1° by 1° grid**, removed long-term linear trends, and calculated departures from each month’s usual conditions. Removing trends also helps correct “model drift”—slow, artificial changes that can occur even when external forcing remains unchanged.

Most modes were identified using *empirical orthogonal function analysis*. In everyday terms, this technique searches a changing map for recurring shapes, then produces an index showing how strongly each shape appears over time. Unlike a fixed geographical box, it can accommodate a model whose climate pattern is slightly displaced.

The team also applied filters to separate timescales: **2–9 years for El Niño**, and a **10-year low-pass filter** to emphasise slower Pacific and Atlantic variability.

## 3. Key Findings

The overall result was encouraging but uneven: models generally reproduced the broad climate patterns, while their amplitudes and regional details differed.

**Atmospheric patterns were particularly consistent.** The North Atlantic Oscillation describes a pressure contrast across the North Atlantic; the Southern Annular Mode involves pressure differences between Antarctica and surrounding latitudes. Their modelled spatial patterns correlated with reanalysis at **above 0.95 and above 0.97**, respectively. A correlation near one indicates closely matching geographical patterns, not perfect forecasts.

**Eastern Pacific El Niño was also represented relatively well.** In observations, its leading pattern explained **63.4%** of the filtered tropical Pacific sea-surface temperature variability. Every model captured the broad wedge of warming across the central and eastern tropical Pacific, with spatial correlations exceeding **0.7**.

However, models including **CanESM5, BCC-CSM2-MR, and ACCESS-ESM1-5** pushed the warming too far west. That geographical error matters because the location of tropical Pacific warming helps shape its influence elsewhere.

**Central Pacific El Niño was harder to reproduce.** Its observed pattern explained only **8.1%** of variability. Although most models achieved correlations above **0.5**, some showed weak or negative correlations. Several misplaced warming into the western or eastern Pacific.

The **Indian Ocean Dipole** showed substantial variation between models. Its observed pattern explained **12.7%** of tropical Indian Ocean temperature variability, compared with roughly **9.5%–31.5%** across simulations. It appeared as the second-leading pattern in most models but the leading pattern in seven.

The **Subsurface Dipole Mode**, based on heat stored in the upper **500 metres**, was the dominant pattern in every model and ORAS5. It explained **21%** of reanalysis variability, versus **14.4% to over 40%** in models.

The **Atlantic Multidecadal Oscillation** was another weak spot. **Ten of 23 models** produced cooling in part of the western-central North Atlantic where the observed warm-phase pattern was broadly warm. Correlations were only about **0.2–0.7**.

Timing was broadly realistic too: observed El Niño variability concentrated around **2–7 years**, while slower Pacific and Atlantic modes operated over decades. Longer simulations revealed more low-frequency variation than the shorter observational records could capture.

## 4. Significance & Real-World Implications

The immediate benefit is practical: researchers can download ready-made indices and spatial patterns rather than repeatedly processing huge model archives.

That can support studies asking how much regional sea-level change, ocean heat variation, or short-term temperature trends arise from internal fluctuations rather than external forcing. For example, researchers investigating monsoon variability can examine connections with Indian and Pacific Ocean modes more efficiently.

The resource may also help improve models. Persistent errors in where Pacific warming occurs, or how North Atlantic temperatures vary, identify processes requiring closer investigation. Better representations could strengthen the evidence used in climate-risk assessments and adaptation planning, although this study does not itself demonstrate improved forecasts.

## 5. Broader Takeaways

The key warning is that **recognisable patterns do not guarantee accurate regional impacts**. Models can capture a mode’s overall shape while misrepresenting its strength, position, or timescale.

There is another important limitation: pre-industrial simulations and modern observations represent different climate conditions. The authors explicitly caution against treating their comparison as a rigorous ranking of model skill. Removing observational trends cannot fully remove human influence on climate variability.

Ultimately, this dataset provides a clearer window onto the climate system’s natural fluctuations. Its value lies in making those fluctuations easier to study—while keeping their uncertainties visible when interpreting past changes and preparing for future risks.

---

*Generated by PDF Summarizer using Gemini API*
*Source: essd-18-5463-2026.pdf*
