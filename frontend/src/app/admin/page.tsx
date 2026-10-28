import { Authenticated } from "@/components/authenticated";
import UserManagement from "@/components/user-management";
export default function AdminPage() { return <Authenticated permission="users:manage"><UserManagement /></Authenticated>; }
