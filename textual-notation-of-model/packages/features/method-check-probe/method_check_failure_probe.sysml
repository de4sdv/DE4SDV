// Throwaway probe for PR #359: Syside must reject this file, so the Method
// Check's export fails and its failure report job runs. Never merge.
package MethodCheckFailureProbe {
    part probe : TypeThatDoesNotExistAnywhere;
}
