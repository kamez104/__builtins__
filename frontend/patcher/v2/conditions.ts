import { pluginSelf } from "millennium-lib"
import { Conditions, ConditionsStore, ThemeItem, ConditionalControlFlowType as ModuleType } from "../../types/types"
import { evaluatePatch } from "../dispatcher"

export const evaluateConditions = (theme: ThemeItem, title: string, classes: string[], document: Document): void => {

    const themeConditions: Conditions = theme.data.Conditions
    const savedConditions: ConditionsStore = pluginSelf.conditionals[theme.native]

    for (const condition in themeConditions) {

        if (!themeConditions.hasOwnProperty(condition)) {
            return 
        }

        if (condition in savedConditions) {
            const patch = themeConditions[condition].values[savedConditions[condition]]

            evaluatePatch(ModuleType.TargetCss, patch, title, classes, document)
            evaluatePatch(ModuleType.TargetJs, patch, title, classes, document)
        }
    }
}