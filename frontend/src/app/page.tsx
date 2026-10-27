import { Authenticated } from "@/components/authenticated";
import KnowledgeWorkspace from "@/components/knowledge-workspace";
export default function Home() { return <Authenticated><KnowledgeWorkspace /></Authenticated>; }
